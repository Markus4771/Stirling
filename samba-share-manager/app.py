#!/usr/bin/env python3
"""Small stdlib-only LAN UI; runs without root privileges."""
import base64, hmac, hashlib, html, json, os, subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

AUTH='/etc/samba-share-manager/auth.json'
HOST=os.environ.get('SHARE_GUI_HOST','0.0.0.0')
PORT=int(os.environ.get('SHARE_GUI_PORT','8765'))

STYLE='''<style>body{font:16px system-ui,sans-serif;background:#f3f5f9;color:#18243a;margin:0}main{max-width:820px;margin:50px auto;padding:22px}.card{background:white;padding:28px;border-radius:14px;margin:20px 0;box-shadow:0 3px 15px #2231}input,button,select{padding:12px 14px;font:inherit;border-radius:7px;border:1px solid #bbc4d2}input{width:min(90%,350px)}button{background:#215bd6;color:#fff;border:0;cursor:pointer}button.danger{background:#b42332}table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:15px;border-bottom:1px solid #ddd}.muted{color:#64718a}.err{color:#b42332}.ok{color:#126b45}code{background:#f3f5f9;padding:4px;border-radius:4px}</style>'''

def helper(*args):
    p=subprocess.run(['/usr/bin/sudo','-n', '/usr/local/lib/samba-share-manager/helper.py',*args],capture_output=True,text=True,timeout=15)
    try:return json.loads(p.stdout)
    except ValueError:return {'ok':False,'error':(p.stderr or 'Unbekannter Fehler')[-300:]}

class Handler(BaseHTTPRequestHandler):
    def authenticated(self):
        h=self.headers.get('Authorization','')
        if not h.startswith('Basic '): return False
        try:
            raw=base64.b64decode(h[6:],validate=True).decode()
            username,password=raw.split(':',1)
            auth=json.load(open(AUTH))
            derived=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(auth['salt']),int(auth['rounds']))
            return username=='admin' and hmac.compare_digest(derived.hex(),auth['digest'])
        except (ValueError, KeyError, UnicodeError, OSError): return False

    def respond(self, code, content, auth_needed=False):
        content=('<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Samba-Freigaben</title>'+STYLE+content+'</html>').encode()
        self.send_response(code)
        self.send_header('Content-Type','text/html; charset=utf-8')
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
        if auth_needed:self.send_header('WWW-Authenticate','Basic realm="Samba Freigaben", charset="UTF-8"')
        self.end_headers(); self.wfile.write(content)

    def guard(self):
        if not self.authenticated():
            self.respond(401,'<main><h1>Anmeldung erforderlich</h1></main>',True);return False
        return True

    def page(self,message='',is_error=False):
        data=helper('list')
        rows=''
        for share in data.get('shares',[]):
            name=html.escape(share['name']);path=html.escape(share['path'])
            rows+=f'''<tr><td><strong>{name}</strong><br><span class="muted"><code>{path}</code></span></td><td>
            <form method="post" action="/update"><input type="hidden" name="name" value="{name}">
            <input type="hidden" name="preset" value="{'input' if '/pipeline/watchedFolders/' in path else 'output' if '/pipeline/finishedFolders/' in path else 'general'}">
            <select name="writable"><option value="yes" {'selected' if share.get('writable') else ''}>Schreiben erlaubt</option>
            <option value="no" {'selected' if not share.get('writable') else ''}>Nur lesen</option></select>
            <button type="submit">Speichern</button></form>
            <form method="post" action="/delete"><input type="hidden" name="name" value="{name}"><button class="danger" type="submit">Entfernen</button></form></td></tr>'''
        status=('<p class="'+('err' if is_error else 'ok')+'">'+html.escape(message)+'</p>') if message else ''
        if not data.get('ok'):status='<p class="err">'+html.escape(data.get('error','Fehler'))+'</p>'
        self.respond(200,f'''<main><h1>Samba-Freigaben</h1><p class="muted">Server scanner · verwaltete Freigaben · Samba-Benutzer markus</p>{status}<section class="card"><h2>Neue Freigabe</h2><form method="post" action="/create"><label for="name">Freigabename</label><p><input id="name" name="name" placeholder="z. B. Scan-Eingang" pattern="[a-zA-Z][a-zA-Z0-9_-]{{0,39}}" required></p><label>Ordner</label><p><select name="preset"><option value="general">Allgemein (/srv/samba-shares)</option><option value="input">Stirling PDF Eingang</option><option value="output">Stirling PDF Ausgang</option></select></p><label>Zugriff</label><p><select name="writable"><option value="yes">Lesen und Schreiben</option><option value="no">Nur lesen</option></select></p><button type="submit">Freigabe erstellen</button></form><p class="muted">Der Ordner wird je nach Auswahl im allgemeinen Bereich oder unter Stirling PDF angelegt.</p></section><section class="card"><h2>Vorhandene Freigaben</h2><table><tr><th>Name und Pfad</th><th>Aktion</th></tr>{rows or '<tr><td colspan="2">Noch keine Freigaben</td></tr>'}</table></section><p class="muted">Beim Entfernen werden Dateien auf dem Server nicht gelöscht. Bestehende, anderweitig konfigurierte Freigaben bleiben unverändert.</p></main>''')

    def do_GET(self):
        if not self.guard():return
        if self.path!='/':self.respond(404,'<main>Nicht gefunden</main>');return
        self.page()

    def do_POST(self):
        if not self.guard():return
        if self.path not in ('/create','/update','/delete'):
            self.respond(404,'<main>Nicht gefunden</main>');return
        origin=self.headers.get('Origin')
        expected=f'http://{self.headers.get("Host","")}'
        if origin and origin!=expected:
            self.respond(403,'<main>Ungueltiger Ursprung</main>');return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not (0<length<1024):raise ValueError()
            form=parse_qs(self.rfile.read(length).decode())
            name=form.get('name',[''])[0]
            result=helper(self.path[1:],name,form.get('preset',['general'])[0],form.get('writable',['yes'])[0]) if self.path!='/delete' else helper('delete',name)
            self.page(result.get('message',result.get('error','Fehler')),not result.get('ok'))
        except (ValueError,UnicodeError):self.respond(400,'<main>Ungueltige Anfrage</main>')

if __name__=='__main__':
    print(f'Listening on {HOST}:{PORT}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
