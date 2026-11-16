"""`GET /matters/{id}/entities` lists documents before their articles, articles
in natural number order, with clean labels (review:15, ui:32).

It used to order by (type, label): every Article sorted before every Document
("Article" < "Document"), so in an ingested statute the Document was on the
last page, even when searching its title, and numbers ran 1, 10, 100, 101.
"""
from __future__ import annotations

import random

import pytest

from app.agent_cli import context
from tests.conftest import seed_article, seed_document, seed_source_span


def _document(db_session, m, title, numbers, heading="Record keeping duty {}"):
    doc = seed_document(db_session, repository_id=m["repository_id"], matter_id=m["matter_id"], title=title)
    for number in random.Random(title).sample(numbers, len(numbers)):  # insertion order is not the answer
        span = seed_source_span(db_session, document_id=doc, matter_id=m["matter_id"], quote_text=f"Section {number}.")
        seed_article(db_session, document_id=doc, matter_id=m["matter_id"], source_span_id=span,
                     number=number, heading=heading.format(number))
    return doc


def _page(client, m, **params):
    response = client.get(f"/api/v1/matters/{m['matter_id']}/entities", params=params, headers=m["reviewer_headers"])
    assert response.status_code == 200, response.text
    return response.json()


def test_statute_document_comes_first_and_articles_run_in_numeric_order(client, db_session, matter_with_users):
    m = matter_with_users
    doc = _document(db_session, m, "Delaware Code -- Statutes", [str(n) for n in range(1, 131)])
    for params in ({}, {"q": "Delaware"}, {"q": "delaware code"}):
        page = _page(client, m, limit=50, **params)
        assert page["total"] == 131
        assert page["items"][0] == {"type": "Document", "id": doc, "label": "Delaware Code -- Statutes"}
        labels = [item["label"] for item in page["items"][1:4]]
        assert labels == [f"Delaware Code -- Statutes / {n} Record keeping duty {n}" for n in (1, 2, 3)]
    numbers = [item["label"].split(" / ")[1].split()[0] for item in
               _page(client, m, limit=100, offset=1)["items"] + _page(client, m, limit=100, offset=101)["items"]]
    assert numbers == [str(n) for n in range(1, 131)]


def test_all_documents_precede_articles_grouped_by_document(client, db_session, matter_with_users):
    m = matter_with_users
    zulu = _document(db_session, m, "Zulu Code", ["2", "1"])
    alpha = _document(db_session, m, "Alpha Code", ["10", "9"])
    items = _page(client, m)["items"]
    assert [(i["type"], i["id"]) for i in items[:2]] == [("Document", alpha), ("Document", zulu)]
    assert [i["label"] for i in items[2:]] == [
        "Alpha Code / 9 Record keeping duty 9", "Alpha Code / 10 Record keeping duty 10",
        "Zulu Code / 1 Record keeping duty 1", "Zulu Code / 2 Record keeping duty 2"]


@pytest.mark.parametrize("numbers", [
    ["1", "2", "2א", "3", "9", "10", "10א", "23ט", "100"],
    ["9-20", "9-101", "9-102", "9-1010", "10-1"],
    ["1-1-101", "1-1-1001", "1-2-101", "1-10-1"],
    ["13-7-20", "13A-7-20", "13A-7-100", "75A-33"],
    ["238.31", "238.300", "246.0012", "246.012"],
    ["399", "399-Q", "4503", "4503d"],
])
def test_mixed_statute_numbering_sorts_naturally(client, db_session, matter_with_users, numbers):
    m = matter_with_users
    _document(db_session, m, "Code", numbers)
    labels = [item["label"] for item in _page(client, m)["items"][1:]]
    assert [label.split(" / ")[1].split()[0] for label in labels] == numbers


def test_every_page_is_a_slice_of_one_ordering(client, db_session, matter_with_users):
    m = matter_with_users
    _document(db_session, m, "Beta Code", ["3", "1", "2"])
    _document(db_session, m, "Alpha Code", ["2", "10"])
    _document(db_session, m, "Gamma Code", [])
    for q in ("", "code", "beta", "/ 2", "missing"):
        full = _page(client, m, q=q, limit=100)
        assert full["total"] == len(full["items"])
        for limit in (1, 2, 3, 5):
            for offset in range(full["total"] + 2):
                page = _page(client, m, q=q, limit=limit, offset=offset)
                assert page == {"items": full["items"][offset:offset + limit], "total": full["total"]}, (q, limit, offset)
    assert [i["label"] for i in _page(client, m, q="/ 2")["items"]] == [
        "Alpha Code / 2 Record keeping duty 2", "Beta Code / 2 Record keeping duty 2"]


def test_labels_have_no_dangling_whitespace(client, db_session, matter_with_users):
    m = matter_with_users
    _document(db_session, m, "Code", ["5"], heading="")
    assert [i["label"] for i in _page(client, m)["items"]] == ["Code", "Code / 5"]


def test_agent_context_shares_the_order(db_session, matter_with_users):
    m = matter_with_users
    doc = _document(db_session, m, "Delaware Code -- Statutes", [str(n) for n in range(1, 31)])
    entities = context(db_session, m["contributor_id"], m["matter_id"], "", 5)["entities"]
    assert entities["items"][0]["id"] == doc
    assert [i["label"].split(" / ")[1].split()[0] for i in entities["items"][1:]] == ["1", "2", "3", "4"]
