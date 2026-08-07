"""Resumable runtime-only M-R104 B1 source-section span measurement.

No production file is edited.  One shard per parquet file is atomically
written and content-addressed; merge refuses incomplete/stale/duplicate work.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, sys, tempfile
from pathlib import Path
import pyarrow.parquet as pq
sys.path.insert(0, str(Path(__file__).parent))
from qa_g7_common import SNAPSHOT_ID, capture_row, jurisdiction_for, tuple_key, validate_corpus
from app.definition_links.us_profile import USProfile
from app.definition_links.rules.us_body_preamble_b1 import _B1_TRIGGER_RE, _B1_LOOKAHEAD, _b1_colon_list_branch, _b1_quote_means_branch
MARKER=re.compile(r"§\s*\d+[A-Za-z0-9:.\-]*")
CONFIG=hashlib.sha256(b"mr104-b1-span-v1:marker-section-only").hexdigest()
def span(t):
 for m in _B1_TRIGGER_RE.finditer(t):
  a=t[m.end():m.end()+_B1_LOOKAHEAD]
  if _b1_colon_list_branch(a) or _b1_quote_means_branch(a):
   p=list(MARKER.finditer(t,0,m.start())); n=MARKER.search(t,m.end())
   return (p[-1].start(),n.start()) if p and n else None
 return None
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def shard(snapshot,out,name):
 files,_,_=validate_corpus(snapshot); path=next(p for p in files if p.name==name); raw=path.read_bytes(); identity=hashlib.sha256(raw).hexdigest(); target=out/'shards'/f'{name}.json'
 if target.exists():
  old=json.loads(target.read_text());
  if old['file_sha256']==identity and old['config_hash']==CONFIG:return old
  raise RuntimeError('stale shard')
 orig=USProfile.extract_definitions_from_section
 def proposed(self,text,*,scope,heading_was_derived=False):
  s=span(text) if heading_was_derived else None
  return orig(self,text[s[0]:s[1]] if s else text,scope=scope,heading_was_derived=heading_was_derived)
 before=[]; after=[]; spans=[]; j=jurisdiction_for(path); i=0
 pf=pq.ParquetFile(path)
 for b in pf.iter_batches(columns=['act_id','section_title','text','chapter','section_number'],batch_size=2048):
  for row in b.to_pylist():
   before += [x.record() for x in capture_row(jurisdiction=j,source_file=name,source_row=i,row=row,after=True)]
   s=span(row['text'] or '')
   if s:
    spans.append({'row':i,'start':s[0],'end':s[1]}); USProfile.extract_definitions_from_section=proposed
    try: after += [x.record() for x in capture_row(jurisdiction=j,source_file=name,source_row=i,row=row,after=True)]
    finally: USProfile.extract_definitions_from_section=orig
   else: after += [x.record() for x in capture_row(jurisdiction=j,source_file=name,source_row=i,row=row,after=True)]
   i+=1
 bk={tuple_key(r):r for r in before}; ak={tuple_key(r):r for r in after}; changed=[{'change':'removed',**bk[k]} for k in bk.keys()-ak.keys()]+[{'change':'added',**ak[k]} for k in ak.keys()-bk.keys()]
 data={'snapshot_id':SNAPSHOT_ID,'file':name,'file_sha256':identity,'config_hash':CONFIG,'rows':i,'before':before,'after':after,'keys_before':sorted(map(list,bk)),'keys_after':sorted(map(list,ak)),'span_evidence':spans,'changed':changed}; data['content_hash']=digest(data)
 target.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=target.parent); os.close(fd); Path(tmp).write_text(json.dumps(data,sort_keys=True)); os.replace(tmp,target); return data
def main():
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--file',required=True);a=p.parse_args();print(json.dumps(shard(a.snapshot,a.out,a.file),sort_keys=True))
if __name__=='__main__':main()
