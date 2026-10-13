#!/usr/bin/env python3
"""Small stdlib-only LAN UI; runs without root privileges."""
import base64, hmac, hashlib, html, json, os, subprocess
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

AUTH='/etc/samba-share-manager/auth.json'
HOST=os.environ.get('SHARE_GUI_HOST','0.0.0.0')
PORT=int(os.environ.get('SHARE_GUI_PORT','8765'))

STYLE='''<style>
:root{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#292929;background:#f7f7f6}
*{box-sizing:border-box}body{margin:0} .layout{display:grid;grid-template-columns:minmax(0,1fr);min-height:100vh}
aside{background:#fafafa;border-right:1px solid #e6e6e6;padding:22px 14px}
.brand{font-size:24px;font-weight:750;padding:3px 13px 28px}.brand span{color:#a75551}
.nav{padding:13px 16px;border-radius:8px;font-size:15px}.nav.active{background:#302f2d;color:white;font-weight:650}
main{padding:36px 45px;max-width:1470px;width:100%;margin:auto}header{display:flex;justify-content:space-between;align-items:center;gap:15px;flex-wrap:wrap;margin-bottom:26px}
h1{font-size:25px;font-weight:650;margin:0}h2{font-size:18px;font-weight:650;margin:0 0 18px}
.subtitle,.muted{color:#737373;font-size:14px}.cards{display:grid;grid-template-columns:minmax(310px,430px) minmax(400px,1fr);gap:22px;align-items:start}
.card{background:white;border:1px solid #e5e5e5;border-radius:12px;padding:24px;margin-bottom:16px}
input,select,button{font:inherit;font-size:14px;border-radius:8px}input,select{width:100%;background:#fff;border:1px solid #d8d8d8;padding:11px;margin:7px 0 14px}
label{font-size:13px;font-weight:600;color:#555}button{padding:10px 15px;border:0;background:#353330;color:white;cursor:pointer;font-weight:600}
button.secondary{background:#f1f1f1;color:#333;border:1px solid #e2e2e2}button.danger{background:#fff0f0;color:#a52828}
button:hover{filter:brightness(.94)}form.inline{display:flex;gap:8px;align-items:center;flex-wrap:wrap}form.inline>*{margin:3px 0}
.share{padding:20px 0;border-top:1px solid #eee}.share:first-of-type{border-top:0}.share-head{display:flex;justify-content:space-between;align-items:start;gap:8px}
.share h3{font-size:16px;margin:0 0 5px}.path{font-size:12px;word-break:break-all;color:#737373}
.tag{background:#eff6f0;color:#25713b;padding:5px 9px;border-radius:6px;font-size:12px}.credentials{display:grid;grid-template-columns:1fr 1fr auto;gap:9px;align-items:end}.credentials input{margin-bottom:0}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.actions{margin-top:10px}.notice{padding:13px 16px;border-radius:8px;border:1px solid #cddacc;background:#f5faf5;margin-bottom:20px}.notice.err{background:#fff6f6;border-color:#edcbcb;color:#922}
@media(max-width:1000px){.cards{grid-template-columns:1fr}.layout{grid-template-columns:1fr}aside{display:none}main{padding:20px}.credentials{grid-template-columns:1fr}}
</style>'''

def helper(*args,stdin_data=None):
    p=subprocess.run(['/usr/bin/sudo','-n', '/usr/local/lib/samba-share-manager/helper.py',*args],capture_output=True,text=True,timeout=15,input=(stdin_data+'\n' if stdin_data is not None else None))
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

    def page(self,message='',is_error=False,revealed=None):
        data=helper('list')
        rows=''
        for share in data.get('shares',[]):
            name=html.escape(share['name'],quote=True)
            path=html.escape(share['path'],quote=True)
            login=html.escape(share.get('user',''),quote=True)
            preset=share.get('preset','general')
            options=''.join('<option value="'+v+'"'+(' selected' if preset==v else '')+'>'+t+'</option>' for v,t in [('general','Allgemein'),('input','Stirling Eingang'),('output','Stirling Ausgang'),('paperless','Paperless Consume')])
            status='Passwort gesetzt · nicht auslesbar' if share.get('password_set') else 'Noch keine Anmeldedaten'
            shown = revealed is not None and revealed[0]==share['name']
            password_view = ('<input type="text" readonly value="'+html.escape(revealed[1],quote=True)+'" aria-label="Angezeigtes SMB-Passwort">' if shown else '<span class="muted">••••••••</span>')
            rows+=f'''<section class="share"><div class="share-head"><div><h3>{name}</h3><div class="path">{path}</div><div class="muted">SMB-Benutzer: <strong>{login or '–'}</strong> · {status}</div></div><span class="tag">Aktiv</span></div>
            <div class="inline actions"><form method="post" action="/reveal" class="inline"><input type="hidden" name="name" value="{name}"><button type="submit" class="secondary" title="Passwort anzeigen">◉ Passwort anzeigen</button></form><div>{password_view}</div></div>
            <form method="post" action="/credentials"><input type="hidden" name="name" value="{name}"><div class="credentials"><div><label>SMB-Benutzer (frei wählbar)</label><input name="user" value="{login}" pattern="[A-Za-z][A-Za-z0-9_-]{{2,30}}" required autocomplete="off"></div><div><label>Neues SMB-Passwort (optional bei Benutzerwechsel)</label><input type="password" name="password" minlength="12" autocomplete="new-password"></div><button type="submit">Benutzer / Passwort speichern</button></div></form>
            <form method="post" action="/update" class="inline actions"><input type="hidden" name="name" value="{name}"><input type="hidden" name="preset" value="{preset}">
            <select name="writable" style="width:auto"><option value="yes" {'selected' if share.get('writable') else ''}>Lesen und Schreiben</option><option value="no" {'selected' if not share.get('writable') else ''}>Nur lesen</option></select><button class="secondary">Rechte speichern</button></form>
            <form method="post" action="/set-path" class="inline actions"><input type="hidden" name="name" value="{name}"><input name="path" value="{path}" style="flex:1;min-width:190px" required><button class="secondary">Pfad übernehmen</button></form>
            <form method="post" action="/grant-acl" class="actions"><input type="hidden" name="name" value="{name}"><button type="submit" class="secondary">Stirling-Zugriffsrechte setzen</button></form>
            <form method="post" action="/delete" class="actions"><input type="hidden" name="name" value="{name}"><button class="danger">Freigabe entfernen</button></form></section>'''
        notice=('<div class="notice'+(' err' if is_error else '')+'">'+html.escape(message)+'</div>') if message else ''
        if not data.get('ok'):notice='<div class="notice err">'+html.escape(data.get('error','Fehler'))+'</div>'
        self.respond(200,f'''<div class="layout">
        <main><header><div><h1>Samba-Freigaben</h1><p class="subtitle">Freigaben, Benutzer und Zugriffsrechte verwalten</p></div><span class="tag">Port {PORT}</span></header>{notice}
        <div class="cards"><section class="card"><h2>Neue Freigabe</h2><form method="post" action="/create"><label>Freigabename</label><input name="name" pattern="[a-zA-Z][a-zA-Z0-9_-]{{0,39}}" placeholder="z. B. Scan-Ausgang" required>
        <label>Ordner</label><select name="preset"><option value="general">Allgemein (/srv/samba-shares)</option><option value="input">Stirling PDF Eingang</option><option value="output">Stirling PDF Ausgang</option><option value="paperless">Paperless-Consume</option></select>
        <label>Schreibrechte</label><select name="writable"><option value="yes">Lesen und Schreiben</option><option value="no">Nur lesen</option></select>
        <label>SMB-Benutzer (z. B. TestSamba; 3–31 Zeichen)</label><input name="user" placeholder="z. B. TestSamba" pattern="[A-Za-z][A-Za-z0-9_-]{{2,30}}" required autocomplete="off"><label>SMB-Passwort (mindestens 12 Zeichen)</label><input type="password" name="password" minlength="12" required autocomplete="new-password"><button type="submit">Freigabe erstellen</button></form><p class="muted">Freigabe und eigener SMB-Zugang werden zusammen angelegt. Anschließend kannst du den Zugang rechts bearbeiten.</p>
        <p class="muted">Paperless Consume muss denselben Ordner sehen (z. B. durch Einbinden der Freigabe). Nur die Freigabe zu erstellen löst noch keinen Import aus.</p></section>
        <section class="card"><h2>Vorhandene Freigaben ({len(data.get('shares',[]))})</h2>{rows or '<p class="muted">Noch keine Freigaben vorhanden.</p>'}</section></div>
        </main></div>''')

    def do_GET(self):
        if not self.guard():return
        if self.path!='/':self.respond(404,'<main>Nicht gefunden</main>');return
        self.page()

    def do_POST(self):
        if not self.guard():return
        if self.path not in ('/create','/update','/delete','/set-path','/credentials','/reveal','/grant-acl'):
            self.respond(404,'<main>Nicht gefunden</main>');return
        origin=self.headers.get('Origin')
        expected=f'http://{self.headers.get("Host","")}'
        if origin and origin!=expected:
            self.respond(403,'<main>Ungueltiger Ursprung</main>');return
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not (0<length<4096):raise ValueError()
            form=parse_qs(self.rfile.read(length).decode())
            name=form.get('name',[''])[0]
            if self.path=='/reveal':
                result=helper('reveal',name)
                if result.get('ok'):
                    self.page('Passwort nur auf dieser Ansicht sichtbar; Browserfenster nach Nutzung schließen.',revealed=(name,result['password']))
                else:
                    self.page(result.get('error','Passwort nicht verfügbar'),True)
                return
            result=(helper('grant-acl',name) if self.path=='/grant-acl' else helper('set-path',name,form.get('path',[''])[0]) if self.path=='/set-path' else helper('credentials',name,form.get('user',[''])[0],stdin_data=form.get('password',[''])[0]) if self.path=='/credentials' else helper('delete',name) if self.path=='/delete' else helper('create',name,form.get('preset',['general'])[0],form.get('writable',['yes'])[0],form.get('user',[''])[0],stdin_data=form.get('password',[''])[0]) if self.path=='/create' else helper('update',name,form.get('preset',['general'])[0],form.get('writable',['yes'])[0]))
            self.page(result.get('message',result.get('error','Fehler')),not result.get('ok'))
        except (ValueError,UnicodeError):self.respond(400,'<main>Ungueltige Anfrage</main>')

if __name__=='__main__':
    print(f'Listening on {HOST}:{PORT}',flush=True)
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
