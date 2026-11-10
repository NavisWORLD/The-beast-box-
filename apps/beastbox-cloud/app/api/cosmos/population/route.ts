import {storageConfig, getBlob} from '@/lib/cosmos/azure-blob.mjs';
import {listRegistered} from '@/lib/cosmos/cosmos-store.mjs';
import {populationFromBlobs} from '@/lib/cosmos/one-population.mjs';

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

/**
 * Registered beasts, from beasts/<id>/state.json only.
 * Storage off, or a missing state file, contributes nothing. No stand-in is written.
 */
export async function GET() {
  const headers = {'Cache-Control': 'no-store'};
  const cfg = storageConfig();
  if (!cfg) return Response.json({ok: true, configured: false, creatures: populationFromBlobs({configured: false, blobs: []})}, {headers});
  try {
    const ids = await listRegistered(cfg);
    const blobs = [];
    for (const id of ids) {
      const path = `beasts/${id}/state.json`;
      try {
        const blob = await getBlob(cfg, path);
        if (!blob || typeof blob.text !== 'string') blobs.push({path, missing: true});
        else blobs.push({path, text: blob.text});
      } catch {
        blobs.push({path, missing: true});
      }
    }
    return Response.json({ok: true, configured: true, creatures: populationFromBlobs({configured: true, blobs})}, {headers});
  } catch {
    return Response.json({ok: true, configured: true, creatures: []}, {headers});
  }
}
