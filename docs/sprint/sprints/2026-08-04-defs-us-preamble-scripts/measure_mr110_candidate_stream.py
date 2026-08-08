"""Runtime-only B1 candidate-stream prototype; supersedes rejected A/B slices."""
from __future__ import annotations

import argparse, json, multiprocessing, re, sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pyarrow.parquet as pq

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from qa_g7_common import SNAPSHOT_ID, capture_row, jurisdiction_for, tuple_key, validate_corpus, write_json, write_jsonl


def _qualified(text, candidates):
    """Keep unquoted candidates; a quoted term needs its own defining verb."""
    from app.definition_links.us_profile import _MEANS_IDIOM_GAP_RE, _QUOTE_TERM_RE
    accepted = []
    for candidate in candidates:
        term = candidate.terms[0]
        quoted = False
        defining = False
        for match in _QUOTE_TERM_RE.finditer(text):
            if match.group(1).strip() == term:
                quoted = True
                defining |= bool(_MEANS_IDIOM_GAP_RE.match(text[match.end():match.end()+200]))
        if not quoted or defining:
            accepted.append(candidate)
    return accepted


def _file(path_text):
    from app.definition_links.profiles import get_profile
    from app.definition_links.rules import registry
    from app.definition_links.rules.us_body_preamble_b1 import _b1_trigger_colon_or_quote_means
    from app.definition_links.us_profile import USProfile, derive_heading_from_body
    path=Path(path_text); code=jurisdiction_for(path); profile=get_profile(code)
    od, oe=USProfile.derive_heading_from_body, USProfile.extract_definitions_from_section; active=set()
    def derive(self, heading, body):
        base=derive_heading_from_body(heading, body)
        if base is not None: return base
        for rule in registry.body_preamble_rules_for(self.code):
            value=rule.derive_heading(body)
            if value is None: continue
            if rule.derive_heading is _b1_trigger_colon_or_quote_means:
                if not _qualified(body, oe(self, body, scope='law-wide', heading_was_derived=True)):
                    return None
                active.add(body)
            return value
        return None
    def extract(self, text, *, scope, heading_was_derived=False):
        got=oe(self,text,scope=scope,heading_was_derived=heading_was_derived)
        return _qualified(text,got) if heading_was_derived and text in active else got
    before=[]; after=[]; USProfile.derive_heading_from_body=derive; USProfile.extract_definitions_from_section=extract
    try:
      for i,b in enumerate(pq.ParquetFile(path).iter_batches(columns=['act_id','section_title','text','chapter','section_number'],batch_size=4096)):
       for j,row in enumerate(b.to_pylist()):
        n=i*4096+j; USProfile.derive_heading_from_body=od; USProfile.extract_definitions_from_section=oe
        before += [x.record() for x in capture_row(jurisdiction=code,source_file=path.name,source_row=n,row=row,after=True)]
        USProfile.derive_heading_from_body=derive; USProfile.extract_definitions_from_section=extract
        after += [x.record() for x in capture_row(jurisdiction=code,source_file=path.name,source_row=n,row=row,after=True)]
        active.discard((row['text'] or ''))
    finally: USProfile.derive_heading_from_body=od; USProfile.extract_definitions_from_section=oe
    b={tuple_key(x):x for x in before}; a={tuple_key(x):x for x in after}; out=[]
    for change,left,right in [('removed',b,a),('added',a,b)]:
      for key in left.keys()-right.keys():
       r=left[key]; family='source_held_hi' if r['jurisdiction']=='US-HI' else 'source_held_fed' if r['jurisdiction']=='US-FED' else 'quoted_candidate_without_defining_relation'
       out.append({'change':change,'classification':family,**r})
    return out

def main():
 p=argparse.ArgumentParser(); p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=1);a=p.parse_args()
 files,rows,_=validate_corpus(a.snapshot); chosen=files[a.shard::a.shards]
 with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('fork')) as pool: changed=[r for x in pool.map(_file,map(str,chosen)) for r in x]
 changed.sort(key=lambda r:(tuple_key(r),r['change'])); a.out.mkdir(parents=True,exist_ok=True)
 result={'schema':'lexgraph.mr110.candidate-stream.v1','snapshot_id':SNAPSHOT_ID,'files':len(files),'rows':rows,'shard':[a.shard,a.shards],'changed_key_count':len(changed),'classification_totals':dict(sorted(Counter(r['classification'] for r in changed).items())),'ledger_sha256':write_jsonl(a.out/'changed.jsonl',changed)}
 write_json(a.out/'summary.json',result);print(json.dumps(result,sort_keys=True))
if __name__=='__main__': main()
