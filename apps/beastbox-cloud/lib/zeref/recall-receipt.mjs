// Verifiable recall receipt (beastbox-recall-v1). Pure: no clock, no storage, no network.
// Additive to the legacy self-memory id. It does not read or write memory entries.
// Spec: docs/recall-receipt-v1.md
import {createHash} from 'node:crypto';

export const RECALL_HASH_SPEC='beastbox-recall-v1';
export const RECALL_HASH_NOTE='SHA-256 hex of UTF-8 canonical JSON (sorted keys, no spaces) under beastbox-recall-v1. Keys: created_at, role, source, spec, text, thread_id. Text is NFC, LF endings, trailing whitespace removed.';
const UTC_ISO=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z$/;
const THREAD_ID=/^[a-f0-9]{32}$/;

/** UTC ISO-8601 (`…Z`, optional fraction) or empty. Receipt identity only. */
export function recallUtc(value){return typeof value==='string'&&UTC_ISO.test(value)?value:'';}
/** Guestbook thread id (32 lowercase hex) or empty. */
export function recallThreadId(value){return typeof value==='string'&&THREAD_ID.test(value)?value:'';}

/**
 * Canonical entry text: NFC, CRLF/CR -> LF, trailing spaces and tabs removed
 * from each line, then trailing spaces, tabs, and line feeds removed from the end.
 * Leading whitespace and internal spaces stay.
 */
export function canonicalRecallText(text){
 const nfc=String(text??'').normalize('NFC');
 const lf=nfc.replace(/\r\n/g,'\n').replace(/\r/g,'\n');
 return lf.split('\n').map(line=>line.replace(/[ \t]+$/g,'')).join('\n').replace(/[ \t\n]+$/g,'');
}

const str=v=>typeof v==='string'?v:'';

/** Canonical JSON: the six keys, sorted, no spaces. `spec` is always beastbox-recall-v1. */
export function canonicalRecallJson(fields={}){
 const body={
  created_at:str(fields.created_at),
  role:str(fields.role),
  source:str(fields.source),
  spec:RECALL_HASH_SPEC,
  text:canonicalRecallText(fields.text),
  thread_id:str(fields.thread_id),
 };
 const keys=Object.keys(body).sort();
 return '{'+keys.map(k=>JSON.stringify(k)+':'+JSON.stringify(body[k])).join(',')+'}';
}

/** Full 64-char hex SHA-256 of the canonical JSON, UTF-8, no trailing newline. */
export function entrySha256(fields){
 return createHash('sha256').update(canonicalRecallJson(fields),'utf8').digest('hex');
}

/** Additive receipt fields. `role`, `source`, `thread_id`, and `created_at` are the strings inside the hash. */
export function recallReceiptBody(fields){
 const json=canonicalRecallJson(fields);
 const body=JSON.parse(json);
 return {
  entry_sha256:createHash('sha256').update(json,'utf8').digest('hex'),
  entry_hash_spec:RECALL_HASH_SPEC,
  entry_hash_note:RECALL_HASH_NOTE,
  role:body.role,source:body.source,thread_id:body.thread_id,created_at:body.created_at,
 };
}
