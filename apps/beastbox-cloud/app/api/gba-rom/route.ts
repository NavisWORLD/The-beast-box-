import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
const RELEASE = 'https://github.com/NavisWORLD/Cosmic-synapse-the-living-universe-sim-engine-/releases/download/lost-cosmos-v11.2-spark/lost-cosmos-v11.2-spark.gba';
const MAX_BYTES = 1_500_000;

export async function GET() {
  try {
    const upstream = await fetch(RELEASE, { redirect: 'follow', cache: 'no-store' });
    if (!upstream.ok || !upstream.body) return NextResponse.json({ error: 'Lost Cosmos V11.2 Spark ROM is unavailable' }, { status: 502 });
    const reader = upstream.body.getReader();
    const chunks: Uint8Array[] = [];
    let total = 0;
    while (true) {
      const next = await reader.read();
      if (next.done) break;
      total += next.value.byteLength;
      if (total > MAX_BYTES) {
        await reader.cancel();
        return NextResponse.json({ error: 'Lost Cosmos ROM exceeded the size cap' }, { status: 502 });
      }
      chunks.push(next.value);
    }
    const body = new Uint8Array(total);
    let at = 0;
    for (const chunk of chunks) {
      body.set(chunk, at);
      at += chunk.byteLength;
    }
    return new Response(body, {
      headers: {
        'Content-Type': 'application/octet-stream',
        'Content-Length': String(total),
        'Cache-Control': 'public, max-age=3600',
        'X-Content-Type-Options': 'nosniff',
      },
    });
  } catch {
    return NextResponse.json({ error: 'Lost Cosmos V11.2 Spark ROM is unavailable' }, { status: 502 });
  }
}
