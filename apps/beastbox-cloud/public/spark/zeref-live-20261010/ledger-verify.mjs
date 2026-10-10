import {sha256Hex} from '../sha.mjs';

/** Verify the existing Python ledger's exact serialized bytes.
 * Re-serializing in JS loses Python's 1.0/exponent spelling, changing hashes.
 */
export function verifyPublishedLedger(text,manifest){
 if(typeof text!=='string'||!text.endsWith('\n'))throw Error('Ledger framing changed');
 let previous='0'.repeat(64),number=0;
 const rows=text.slice(0,-1).split('\n').map(raw=>{
  const row=JSON.parse(raw),hash=row.event_sha256;
  if(row.schema!=='persistent-substrate-state-event-v1'||!/^[a-f0-9]{64}$/.test(hash)||row.event_index!==++number||row.previous_event_sha256!==previous)throw Error('Ledger sequence mismatch');
  const prefix='{"event_index":'+row.event_index+',"event_sha256":'+JSON.stringify(hash)+',"kind":';
  if(!raw.startsWith(prefix))throw Error('Canonical ledger framing changed');
  const unsigned=raw.replace(',"event_sha256":'+JSON.stringify(hash),'');
  if(sha256Hex(unsigned)!==hash)throw Error('Ledger event hash mismatch');
  previous=hash;return row;
 });
 if(previous!==manifest.tip_sha256||number!==manifest.record_count||sha256Hex(text)!==manifest.ledger_file_sha256)throw Error('Ledger manifest mismatch');
 return {rows,count:number,tip:previous};
}
