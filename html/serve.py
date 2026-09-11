"""Serve the Beast Box web client beside the canonical runtime API.

This is a transport adapter only: business logic remains in beastbox.cosmic_web.CosmicApp.
A per-process HttpOnly session cookie gates state-changing API calls; host secrets never enter the bundle.
"""
from __future__ import annotations
import argparse
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import urllib.parse
import json
import mimetypes
from beastbox.cosmic_web import CosmicApp, validate_bind_host
ROOT=Path(__file__).resolve().parent;MAX_REQUEST=1024*1024
class Server(ThreadingHTTPServer):
    app:CosmicApp;session:str
class Handler(BaseHTTPRequestHandler):
    server_version='BeastBoxWeb/1'
    @property
    def s(self)->Server:return self.server # type: ignore[return-value]
    def headers(self,status,ctype,set_cookie=False):
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','no-referrer');self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()');self.send_header('Content-Security-Policy',"default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data: blob:; connect-src 'self'; worker-src 'self'; manifest-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if set_cookie:self.send_header('Set-Cookie',f'beastbox_session={self.s.session}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
    def json(self,status,payload):
        raw=json.dumps(payload,sort_keys=True,default=str).encode();self.headers(status,'application/json; charset=utf-8');self.wfile.write(raw)
    def authorized(self):
        c=SimpleCookie();c.load(self.headers.get('Cookie',''));v=c.get('beastbox_session');return bool(v) and secrets.compare_digest(v.value,self.s.session)
    def do_GET(self):
        path=urllib.parse.urlparse(self.path).path
        if path in ('/','/html','/html/'):
            raw=(ROOT/'index.html').read_bytes();self.headers(200,'text/html; charset=utf-8',True);self.wfile.write(raw);return
        if path.startswith('/html/'):
            rel=path[len('/html/'):] or 'index.html';target=(ROOT/rel).resolve()
            if (ROOT not in target.parents and target!=ROOT) or not target.is_file():self.json(404,{'error':'not found'});return
            ctype=mimetypes.guess_type(target.name)[0] or 'application/octet-stream';self.headers(200,ctype+('; charset=utf-8' if ctype.startswith(('text/','application/javascript')) else ''));self.wfile.write(target.read_bytes());return
        status,payload=self.s.app.dispatch('GET',path);self.json(status,payload)
    def do_POST(self):
        if not self.authorized():self.json(403,{'error':'invalid session'});return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<=length<=MAX_REQUEST:raise ValueError
            raw=self.rfile.read(length);body=json.loads(raw.decode()) if raw else {}
            if not isinstance(body,dict):raise ValueError
        except Exception:self.json(400,{'error':'invalid JSON request'});return
        path=urllib.parse.urlparse(self.path).path;status,payload=self.s.app.dispatch('POST',path,body);self.json(status,payload)
    def log_message(self,*args):pass
def main():
    p=argparse.ArgumentParser(description='Beast Box standalone web runtime');p.add_argument('--data-dir',default='./my-beast');p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8081);a=p.parse_args();validate_bind_host(a.host);s=Server((a.host,a.port),Handler);s.app=CosmicApp(a.data_dir);s.session=secrets.token_urlsafe(32);print(f'BEAST BOX WEB RUNTIME\nUI: http://{a.host}:{a.port}/html/\nDATA: {Path(a.data_dir).expanduser().resolve()}\nAUTHORITY: ALL OFF');
    try:s.serve_forever()
    finally:s.server_close()
if __name__=='__main__':main()
