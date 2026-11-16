"""Real database proof across local agent creation and lawyer collaboration."""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest
from sqlalchemy import select, func
from app.models.assertion import Assertion
from app.models.audit_event import AuditEvent
from app.mcp.server import create_server
from tests.conftest import seed_document, seed_source_span, seed_matter, seed_repository, new_id, assertion_payload


@pytest.fixture
def suggestion(db_session, matter_with_users):
    m = matter_with_users
    doc = seed_document(db_session, repository_id=m['repository_id'], matter_id=m['matter_id'], title='Service agreement')
    span = seed_source_span(db_session, document_id=doc, matter_id=m['matter_id'], quote_text='Confidentiality shall survive termination.')
    return dict(repository_id=m['repository_id'], matter_id=m['matter_id'], assertion_type='SURVIVES_TERMINATION',
                proposition='The confidentiality obligation survives termination.', subject_entity={'type': 'Document', 'id': doc},
                evidence=[{'source_span_id': span, 'evidence_role': 'primary_basis'}], explanation='The survival sentence supplies the basis.',
                agent={'platform': 'claude-code', 'model': 'test-model', 'run_id': 'test-run'}, confidence=0.8)


def test_agent_lawyer_lifecycle(client, db_session, matter_with_users, suggestion):
    m = matter_with_users
    created = client.post('/api/v1/agent/assertions', json=suggestion, headers=m['contributor_headers'])
    assert created.status_code == 201, created.text
    a = created.json(); aid = a['id']; path = f'/api/v1/assertions/{aid}'
    assert (a['origin'], a['status'], a['confidence']) == ('model_suggested', 'proposed', 0.8)
    assert a['agent_provenance'] == suggestion['agent']
    detail = client.get(path, headers=m['reviewer_headers']).json()
    assert detail['evidence'][0]['quote_text'] == 'Confidentiality shall survive termination.'
    assert detail['comments'][0]['comment_text_raw'] == suggestion['explanation']
    assert client.put(path+'/revisions/1/rating', json={'strength': 5, 'rationale': 'Strong textual basis'}, headers=m['rater_headers']).status_code in (200, 201)
    assert client.get(path, headers=m['reviewer_headers']).json()['status'] == 'proposed'
    assert client.get(f"/api/v1/matters/{m['matter_id']}/graph", headers=m['reviewer_headers']).json()['edges'] == []
    revised = client.patch(path, json={'proposition':'Confidentiality survives termination under the survival clause.', 'expected_revision_number':1}, headers=m['reviewer_headers'])
    assert revised.status_code == 200, revised.text
    assert revised.json()['current_revision_number'] == 2
    assert client.get(path+'/revisions/1/ratings/summary', headers=m['reviewer_headers']).json()['count'] == 1
    assert client.get(path+'/revisions/2/ratings/summary', headers=m['reviewer_headers']).json()['count'] == 0
    assert client.patch(path, json={'proposition':'Stale overwrite', 'expected_revision_number':1}, headers=m['reviewer_headers']).status_code == 409
    assert client.post(path+'/accept', headers=m['reviewer_headers']).json()['status'] == 'accepted'
    assert client.patch(path, json={'proposition':'Author bypass'}, headers=m['contributor_headers']).status_code == 403
    again = client.patch(path, json={'proposition':'A reviewer proposes a narrower survival interpretation.'}, headers=m['reviewer_headers'])
    assert again.json()['status'] == 'proposed'
    assert again.json()['reviewed_by'] is None
    assert again.json()['agent_provenance'] == suggestion['agent']
    events = list(db_session.scalars(select(AuditEvent).where(AuditEvent.assertion_id == aid)))
    assert sum(e.event_type == 'assertion_created' for e in events) == 1
    assert sum(e.event_type == 'assertion_agent_provenance' for e in events) == 1


@pytest.mark.parametrize('change', [
    {'save_as':'accepted'}, {'confidence':1.1}, {'agent':{'platform':' '}},
    {'subject_entity':{'type':'Document','id':'not-present'}},
    {'subject_entity':{'type':'Provision','id':'00000000-0000-0000-0000-000000000000'}},
    {'evidence':[{'source_span_id':'missing','evidence_role':'supports'}]},
    {'origin':'user_suggested'}, {'proposition':'   '},
])
def test_invalid_agent_payload_is_atomic(client, db_session, matter_with_users, suggestion, change):
    response = client.post('/api/v1/agent/assertions', json={**suggestion, **change}, headers=matter_with_users['contributor_headers'])
    assert response.status_code == 422, response.text
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 0
    assert db_session.scalar(select(func.count()).select_from(AuditEvent)) == 0


def test_isolation_discovery_duplicates(client, db_session, matter_with_users, suggestion):
    m = matter_with_users
    assert client.post('/api/v1/agent/assertions', json=suggestion, headers=m['outsider_headers']).status_code == 403
    other_repo = seed_repository(db_session, organization_id=m['organization_id'])
    assert client.post('/api/v1/agent/assertions', json={**suggestion, 'repository_id':other_repo}, headers=m['contributor_headers']).status_code == 422
    other_matter = seed_matter(db_session, repository_id=other_repo)
    other_doc = seed_document(db_session, repository_id=other_repo, matter_id=other_matter)
    assert client.post('/api/v1/agent/assertions', json={**suggestion, 'subject_entity':{'type':'Document','id':other_doc}}, headers=m['contributor_headers']).status_code == 422
    for resource in ['entities','source-spans']:
        path = f"/api/v1/matters/{m['matter_id']}/{resource}"
        assert client.get(path, headers=m['outsider_headers']).status_code == 403
        result = client.get(path, params={'limit':1}, headers=m['reviewer_headers']).json()
        assert result['total'] == 1 and len(result['items']) == 1
        assert client.get(path, params={'offset':1}, headers=m['reviewer_headers']).json()['items'] == []
        assert client.get(path, params={'limit':101}, headers=m['reviewer_headers']).status_code == 422
    assert client.post('/api/v1/agent/assertions', json=suggestion, headers=m['contributor_headers']).status_code == 201
    assert client.post('/api/v1/agent/assertions', json=suggestion, headers=m['contributor_headers']).status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Assertion)) == 1


def test_local_cli_and_mcp_share_contract(app, client, matter_with_users, suggestion, tmp_path):
    m = matter_with_users
    env = {**os.environ, 'LEXGRAPH_DATABASE_URL':str(app.state.engine.url), 'LEXGRAPH_AGENT_USER_ID':m['contributor_id']}
    cwd = Path(__file__).resolve().parents[2]
    def cli(*args, payload=None):
        return subprocess.run([sys.executable, '-m', 'app.agent_cli', *args], input=json.dumps(payload) if payload else None,
                              capture_output=True, text=True, env=env, cwd=cwd)
    discovery = cli('context', '--matter-id', m['matter_id'])
    assert discovery.returncode == 0, discovery.stderr
    assert json.loads(discovery.stdout)['entities']['items'][0]['id'] == suggestion['subject_entity']['id']
    created = cli('suggest', payload=suggestion)
    assert created.returncode == 0, created.stderr
    aid = json.loads(created.stdout)['id']
    assert client.get(f'/api/v1/assertions/{aid}', headers=m['reviewer_headers']).json()['origin'] == 'model_suggested'
    assert cli('suggest', payload=suggestion).returncode == 1
    server = create_server(app.state.session_factory, agent_user_id=m['contributor_id'])
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert {'assertion_guide','agent_context','suggest_assertion'} <= names
    payload = {**suggestion, 'proposition':'An independently phrased MCP suggestion.', 'agent':{'platform':'codex'}}
    result = asyncio.run(server.call_tool('suggest_assertion', {'payload':payload}))
    assert result.is_error is False, result
    rows = client.get('/api/v1/assertions', params={'matter_id':m['matter_id']}, headers=m['reviewer_headers']).json()['items']
    assert len(rows) == 2 and {a['agent_provenance']['platform'] for a in rows} == {'claude-code','codex'}
    readonly = create_server(app.state.session_factory)
    assert 'suggest_assertion' not in {t.name for t in asyncio.run(readonly.list_tools())}


@pytest.mark.parametrize('payload', [{'proposition':None}, {'proposition':'<script>bad</script>'}, {'assertion_type':None}, {'subject_entity':None}, {'effective_from':'2030-01-01', 'effective_to':'2029-01-01'}])
def test_edit_validation_preserves_previous_revision(client, matter_with_users, payload):
    m = matter_with_users
    a = client.post('/api/v1/assertions', json=assertion_payload(m['matter_id'], m['repository_id']), headers=m['contributor_headers']).json()
    for suffix in ['', '/revisions']:
        method = client.patch if not suffix else client.post
        assert method(f"/api/v1/assertions/{a['id']}"+suffix, json=payload, headers=m['contributor_headers']).status_code == 422
    assert client.get(f"/api/v1/assertions/{a['id']}", headers=m['contributor_headers']).json()['current_revision_number'] == 1
