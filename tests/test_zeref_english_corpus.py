"""English foundation corpus 001: licences, labels, screening, mix share, held-out exclusion."""
from __future__ import annotations
import gzip,hashlib,json,os,tempfile,unittest
from pathlib import Path
from scripts.zeref_english_corpus_build import screen,LABEL,passages_from_paragraphs
from scripts.zeref_english_mix import mix
from scripts.zeref_english_clarity import word_share
EV=Path(__file__).resolve().parents[1]/"evidence/zeref-english-001"
ALLOWED={"CC-BY-4.0","Public domain (US); Project Gutenberg header, footer and licence text removed"}
def sha(b):return hashlib.sha256(b).hexdigest()
class Manifest(unittest.TestCase):
 def setUp(self):self.m=json.loads((EV/"manifest.json").read_text())
 def test_label_and_licences(self):
  self.assertEqual(self.m["label"],"RECORDED_CORPUS")
  self.assertIn("not Zeref's experience".lower(),self.m["label_note"].lower())
  for s in self.m["sources"]:
   self.assertIn(s["licence"],ALLOWED,s["source"]);self.assertIs(s["model_generated"],False)
   self.assertEqual(len(s["raw_sha256"]),64);self.assertGreater(s["raw_bytes"],0)
  self.assertTrue(set(self.m["licences"])<=ALLOWED)
 def test_model_generated_and_nc_sets_are_excluded(self):
  names=" ".join(e["source"] for e in self.m["excluded_sources"])
  for n in("TinyStories","oasst1","DailyDialog","EmpatheticDialogues"):self.assertIn(n,names)
 def test_data_branch_pin_and_eval_files(self):
  d=self.m["data_branch"];self.assertRegex(d["commit"],r"^[0-9a-f]{40}$")
  self.assertEqual(sha((EV/"wordlist.txt").read_bytes()),self.m["files"]["wordlist.txt"]["sha256"])
  rows=[json.loads(l) for l in (EV/"clarity-heldout.jsonl").read_text().splitlines()]
  self.assertEqual(len(rows),64);self.assertTrue(all(r["label"]==LABEL for r in rows))
class Screen(unittest.TestCase):
 def test_pii_and_toxicity(self):
  self.assertEqual(screen("Write to me at someone@example.com please, it is a nice day today."),"pii_email")
  self.assertEqual(screen("Call me back at 555-123-4567 when the pizza is ready for pickup."),"pii_phone")
  self.assertEqual(screen("Look at https://example.org for the menu of the day, it is long."),"pii_url")
  self.assertEqual(screen("The savage wind blew over the hills and the little house shook."),"toxicity_blocklist")
  self.assertIsNone(screen("The little rabbit hopped over the garden wall and found a carrot."))
 def test_chunking_bounds(self):
  out=passages_from_paragraphs(["word "*30]*20)
  self.assertTrue(out and all(200<=len(p)<=900 for p in out))
class Mix(unittest.TestCase):
 def _corpus(self,d,n=400):
  rows=[{"text":f"passage {i} about a cat and a dog","source":"gutenberg:1" if i%2 else "taskmaster-1:x","kind":"book" if i%2 else "dialogue",
         "licence":"CC-BY-4.0","label":LABEL,"row_sha256":sha(f"passage {i}".encode())} for i in range(n)]
  raw=gzip.compress("".join(json.dumps(r)+"\n" for r in rows).encode(),mtime=0)
  (d/"train.jsonl.gz").write_bytes(raw)
  (d/"manifest.json").write_text(json.dumps({"label":LABEL,"files":{"train.jsonl.gz":{"sha256":sha(raw)}}}))
  (d/"clarity-heldout.jsonl").write_text(json.dumps(rows[1])+"\n")
  return rows
 def test_share_half_and_heldout_excluded(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);rows=self._corpus(d)
   pre=d/"pre.jsonl";pre.write_text("".join(json.dumps({"text":f"old {i}"})+"\n" for i in range(100)))
   rec=mix(d/"train.jsonl.gz",d/"manifest.json",pre,"s1",d/"r.json",share=0.5,book_share=0.6)
   lines=[json.loads(l) for l in pre.read_text().splitlines()]
   self.assertEqual(rec["english_rows_added"],100);self.assertEqual(len(lines),200)
   self.assertEqual(rec["english_rows_by_kind"],{"book":60,"dialogue":40})
   self.assertNotIn(rows[1]["text"],{x["text"] for x in lines})
   self.assertEqual([x["text"] for x in lines[:100]],[f"old {i}" for i in range(100)])  # old rows unchanged
 def test_share_zero_is_exact_old_pool_and_rotation(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self._corpus(d);pre=d/"pre.jsonl";old="".join(json.dumps({"text":f"old {i}"})+"\n" for i in range(10))
   pre.write_text(old);mix(d/"train.jsonl.gz",d/"manifest.json",pre,"s",d/"r.json",share=0);self.assertEqual(pre.read_text(),old)
   a=d/"a.jsonl";b=d/"b.jsonl";a.write_text(old);b.write_text(old)
   mix(d/"train.jsonl.gz",d/"manifest.json",a,"cycle-70",d/"r1.json",share=.5);mix(d/"train.jsonl.gz",d/"manifest.json",b,"cycle-71",d/"r2.json",share=.5)
   self.assertNotEqual(a.read_text(),b.read_text())
 def test_bad_sha_refused(self):
  with tempfile.TemporaryDirectory() as t:
   d=Path(t);self._corpus(d);(d/"manifest.json").write_text(json.dumps({"label":LABEL,"files":{"train.jsonl.gz":{"sha256":"0"*64}}}))
   with self.assertRaises(ValueError):mix(d/"train.jsonl.gz",d/"manifest.json",d/"p.jsonl","s",d/"r.json",share=.5)
class Clarity(unittest.TestCase):
 def test_word_share(self):
  r=word_share(["The cat sat", "Mexicoffal Passionie"],{"the","cat","sat"})
  self.assertEqual(r["words"],5);self.assertEqual(r["dictionary_words"],3);self.assertEqual(r["real_word_share"],0.6)
if __name__=="__main__":unittest.main()
