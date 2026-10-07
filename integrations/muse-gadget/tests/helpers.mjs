import { execFile, spawn } from 'node:child_process';
import { mkdtempSync, readFileSync } from 'node:fs';
import { createServer } from 'node:net';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = dirname(fileURLToPath(import.meta.url));
export const ROOT = resolve(HERE, '..');
export const REPO = resolve(ROOT, '..', '..');
export const APP_LIB = join(REPO, 'apps', 'beastbox-cloud', 'lib', 'companion');
export const PYTHON = process.env.PYTHON || 'python3';
export const genomes = JSON.parse(readFileSync(join(HERE, 'fixtures', 'genomes.json'), 'utf8'));

export function freePort() {
  return new Promise((ok, fail) => {
    const server = createServer();
    server.listen(0, '127.0.0.1', () => { const { port } = server.address(); server.close(() => ok(port)); });
    server.on('error', fail);
  });
}

export function gadgetEnv(stateDir, port) {
  return {
    ...process.env,
    PYTHONPATH: ROOT,
    HOME: stateDir,
    BEASTBOX_GADGET_STATE_DIR: stateDir,
    BEASTBOX_BRIDGE_URL: `http://127.0.0.1:${port}`,
    OLLAMA_HOST: 'http://127.0.0.1:9',
  };
}

export function python(args, { env, input } = {}) {
  return new Promise((ok, fail) => {
    const child = execFile(PYTHON, args, { env, timeout: 60000 }, (error, stdout, stderr) => {
      if (error && error.code !== 1) return fail(new Error(`${args.join(' ')} failed: ${stderr || error.message}`));
      ok({ code: error ? error.code : 0, stdout, stderr });
    });
    if (input !== undefined) child.stdin.end(input);
  });
}

export async function startBridge() {
  const stateDir = mkdtempSync(join(tmpdir(), 'bbx-bridge-'));
  const port = await freePort();
  const env = gadgetEnv(stateDir, port);
  const child = spawn(PYTHON, ['-m', 'beastbox_musegadget', 'bridge', 'serve', '--host', '127.0.0.1', '--port', String(port)], { env, stdio: ['ignore', 'ignore', 'pipe'] });
  let log = '';
  child.stderr.on('data', (chunk) => { log += chunk; });
  const url = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 100; i += 1) {
    try { if ((await fetch(url + '/v1/health')).ok) return { url, env, stateDir, child, log: () => log }; } catch { /* starting */ }
    await new Promise((r) => setTimeout(r, 100));
  }
  child.kill();
  throw new Error('bridge did not start: ' + log);
}

export function memoryStorage() {
  const data = new Map();
  return { getItem: (k) => (data.has(k) ? data.get(k) : null), setItem: (k, v) => data.set(k, String(v)), removeItem: (k) => data.delete(k) };
}
