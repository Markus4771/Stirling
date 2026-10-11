#!/usr/bin/env python3
"""Privileged, narrowly scoped Samba share operations."""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

CONFIG = Path('/etc/samba/share-manager.conf')
SMB_CONF = Path('/etc/samba/smb.conf')
BASE = Path('/srv/samba-shares')
NAME_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]{0,39}$')

def fail(msg):
    print(json.dumps({'ok':False,'error':msg})); sys.exit(1)

def read_entries():
    if not CONFIG.exists(): return {}
    data = {}
    section = None
    for line in CONFIG.read_text().splitlines():
        line=line.strip()
        if line.startswith('[') and line.endswith(']'):
            section=line[1:-1]
            if not NAME_RE.fullmatch(section): fail('Ungueltige verwaltete Konfiguration')
            data[section]={}
        elif section and '=' in line:
            k,v=line.split('=',1); data[section][k.strip()]=v.strip()
    return data

def render(entries):
    lines=['# Automatisch verwaltet. Nicht manuell bearbeiten.','']
    for name, opts in sorted(entries.items()):
        lines += [f'[{name}]']+[f'    {k} = {v}' for k,v in opts.items()]+['']
    return '\n'.join(lines)+'\n'

def put(entries):
    CONFIG.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
    old = CONFIG.read_bytes() if CONFIG.exists() else None
    fd,tmp=tempfile.mkstemp(prefix='.share-manager-', dir=str(CONFIG.parent))
    try:
        with os.fdopen(fd,'w') as f:
            f.write(render(entries)); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp,0o644); os.replace(tmp,CONFIG)
        check=subprocess.run(['testparm','-s'],capture_output=True,text=True)
        if check.returncode:
            if old is None: CONFIG.unlink(missing_ok=True)
            else: CONFIG.write_bytes(old)
            fail('Samba-Konfiguration ungueltig: '+check.stderr[-600:])
        reload_result=subprocess.run(['systemctl','reload','smbd'],capture_output=True,text=True)
        if reload_result.returncode: fail('Konfiguration gespeichert; smbd konnte nicht neu geladen werden: '+reload_result.stderr[-300:])
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def main():
    if os.geteuid()!=0: fail('Root-Berechtigung erforderlich')
    if len(sys.argv)<2 or sys.argv[1] not in ('list','create','delete'): fail('Ungueltige Aktion')
    action=sys.argv[1]
    entries=read_entries()
    if action=='list':
        if len(sys.argv)!=2: fail('Ungueltige Argumente')
        print(json.dumps({'ok':True,'shares':[{'name':n,'path':v.get('path','')} for n,v in sorted(entries.items())]})); return
    if len(sys.argv)!=3: fail('Ungueltige Argumente')
    name=sys.argv[2]
    if not NAME_RE.fullmatch(name): fail('Name: Buchstaben, Zahlen, _ oder -, maximal 40 Zeichen')
    if action=='create':
        if name in entries: fail('Freigabe existiert bereits')
        if name.lower() in SMB_CONF.read_text().lower():
            if re.search(r'^\s*\['+re.escape(name)+r'\]\s*$',SMB_CONF.read_text(),re.I|re.M): fail('Name in smb.conf bereits vergeben')
        directory=BASE/name
        if directory.exists(): fail('Zielordner existiert bereits; keine Uebernahme fremder Daten')
        import pwd
        try: user=pwd.getpwnam('markus')
        except KeyError: fail('Linux-Benutzer markus nicht vorhanden')
        BASE.mkdir(mode=0o755,parents=True)
        directory.mkdir(mode=0o2770)
        os.chown(directory,user.pw_uid,user.pw_gid)
        os.chmod(directory,0o2770)
        entries[name]={'path':str(directory),'browseable':'yes','read only':'no','valid users':'markus','force user':'markus','create mask':'0660','directory mask':'2770'}
        put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe erstellt','path':str(directory)}))
    else:
        if name not in entries: fail('Freigabe nicht gefunden')
        del entries[name]; put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe entfernt. Dateien bleiben erhalten.'}))

if __name__=='__main__': main()
