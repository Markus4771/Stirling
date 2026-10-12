#!/usr/bin/env python3
"""Privileged, narrowly scoped Samba share operations."""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

CONFIG = Path('/etc/samba/share-manager.conf')
SMB_CONF = Path('/etc/samba/smb.conf')
BASE = Path('/srv/samba-shares')
PIPELINE = Path('/opt/Stirling-PDF/pipeline')
PRESETS = {'general': None, 'input': 'watchedFolders', 'output': 'finishedFolders', 'paperless': None}
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
    if len(sys.argv)<2 or sys.argv[1] not in ('list','create','delete','update','set-path','credentials'): fail('Ungueltige Aktion')
    action=sys.argv[1]
    entries=read_entries()
    if action=='list':
        if len(sys.argv)!=2: fail('Ungueltige Argumente')
        print(json.dumps({'ok':True,'shares':[{'name':n,'path':v.get('path',''), 'writable':v.get('read only','no')=='no', 'user':v.get('valid users',''), 'password_set':bool(v.get('valid users','')), 'preset': ('paperless' if v.get('comment','')=='Paperless Consume' else 'input' if '/watchedFolders/' in v.get('path','') else 'output' if '/finishedFolders/' in v.get('path','') else 'general')} for n,v in sorted(entries.items())]})); return
    if (action in ('create','update') and len(sys.argv)!=5) or (action=='delete' and len(sys.argv)!=3) or (action=='set-path' and len(sys.argv)!=4) or (action=='credentials' and len(sys.argv)!=4): fail('Ungueltige Argumente')
    name=sys.argv[2]
    if not NAME_RE.fullmatch(name): fail('Name: Buchstaben, Zahlen, _ oder -, maximal 40 Zeichen')
    if action=='credentials':
        if name not in entries: fail('Freigabe nicht gefunden')
        login=sys.argv[3]
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,30}',login): fail('Benutzer: 3-31 Kleinbuchstaben, Ziffern, _')
        for share,entry in entries.items():
            if share!=name and entry.get('valid users')==login: fail('Samba-Benutzer bereits einer anderen Freigabe zugeordnet')
        password=sys.stdin.readline().rstrip('\n')
        if len(password)<12 or len(password)>256: fail('Passwort muss 12 bis 256 Zeichen haben')
        import pwd
        try: pwd.getpwnam(login)
        except KeyError:
            result=subprocess.run(['useradd','--system','--no-create-home','--shell','/usr/sbin/nologin',login],capture_output=True,text=True)
            if result.returncode: fail('Linux-Benutzer konnte nicht angelegt werden')
        result=subprocess.run(['smbpasswd','-s','-a',login],input=password+'\n'+password+'\n',capture_output=True,text=True,timeout=15)
        if result.returncode: fail('SMB-Passwort konnte nicht gesetzt werden: '+result.stderr[-200:])
        previous=entries[name].get('valid users','')
        entries[name]['valid users']=login
        put(entries)
        print(json.dumps({'ok':True,'message':'Samba-Zugang gespeichert (Passwort wird nicht angezeigt)','user':login}))
        return
    if action=='set-path':
        if name not in entries: fail('Freigabe nicht gefunden')
        supplied=sys.argv[3]
        target=Path(supplied)
        roots=(BASE, PIPELINE/'watchedFolders', PIPELINE/'finishedFolders')
        if not target.is_absolute() or '..' in target.parts or '.' in target.parts:
            fail('Ungueltiger Pfad')
        if not any(root in target.parents for root in roots):
            fail('Pfad ausserhalb der erlaubten Scanverzeichnisse')
        if not target.is_dir() or target.is_symlink() or target.resolve(strict=True)!=target:
            fail('Pfad muss ein existierendes Verzeichnis ohne Symlinks sein')
        relative=next(target.relative_to(root) for root in roots if root in target.parents)
        if any(p.startswith('.') or p in ('processing','error') for p in relative.parts):
            fail('Interne Ordner duerfen nicht freigegeben werden')
        import pwd
        owner=pwd.getpwnam('stirling' if PIPELINE in target.parents else 'markus')
        required='-w' if entries[name].get('read only','no')=='no' else '-r'
        check=subprocess.run(['runuser','-u',owner.pw_name,'--','test',required,str(target)],capture_output=True)
        if check.returncode: fail('Zielordner ist fuer Samba-Benutzer '+owner.pw_name+' nicht ausreichend berechtigt')
        entries[name]['path']=str(target)
        entries[name]['force user']=owner.pw_name
        put(entries)
        print(json.dumps({'ok':True,'message':'Zielpfad geaendert; Dateien nicht verschoben','path':str(target)}))
        return
    if action in ('create','update'):
        preset=sys.argv[3]
        if preset not in PRESETS: fail('Ungueltiger Ordnertyp')
        writable=sys.argv[4]
        if writable not in ('yes','no'): fail('Ungueltige Berechtigung')
        if action=='create' and any(n.casefold()==name.casefold() for n in entries): fail('Freigabe existiert bereits')
        if action=='update' and name not in entries: fail('Freigabe nicht gefunden')
        if action=='create' and re.search(r'^\s*\['+re.escape(name)+r'\]\s*,SMB_CONF.read_text(),re.I|re.M): fail('Name in smb.conf bereits vergeben')
        import pwd
        try:
            user=pwd.getpwnam('markus')
            stirling=pwd.getpwnam('stirling')
        except KeyError: fail('Linux-Benutzer markus oder stirling fehlt')
        if preset in ('general','paperless'):
            directory=(BASE/'Paperless-Consume' if preset=='paperless' else BASE/name)
            owner=user
        else:
            directory=PIPELINE/PRESETS[preset]/name
            owner=stirling
        # Do not change ownership of an existing folder. Pipeline directories
        # are created only if absent and are never removed by this application.
        if action=='create' and directory.exists():
            fail('Zielordner existiert bereits; keine automatische Uebernahme')
        if action=='update' and entries[name].get('path')!=str(directory):
            fail('Pfadwechsel bestehender Freigaben nicht erlaubt: erst Freigabe entfernen, dann neu erstellen')
        if not directory.exists():
            parent=directory.parent
            if preset in ('general','paperless'):
                BASE.mkdir(mode=0o755,parents=True,exist_ok=True)
            elif not parent.is_dir() or parent.is_symlink():
                fail('Stirling-PDF-Zielverzeichnis existiert nicht')
            directory.mkdir(mode=0o2770)
            os.chown(directory,owner.pw_uid,owner.pw_gid)
            os.chmod(directory,0o2770)
        if directory.is_symlink(): fail('Symbolische Links sind nicht erlaubt')
        entries[name]={'path':str(directory),'browseable':'yes','read only':'no' if writable=='yes' else 'yes',
                       'valid users':(entries.get(name,{}).get('valid users','markus')),'force user':owner.pw_name,
                       'comment':('Paperless Consume' if preset=='paperless' else 'Verwaltet durch Samba Share Manager'),
                       'create mask':'0660','directory mask':'2770'}
        put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe gespeichert','path':str(directory)}))
    else:
        if name not in entries: fail('Freigabe nicht gefunden')
        del entries[name]; put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe entfernt. Dateien bleiben erhalten.'}))

if __name__=='__main__': main()
,SMB_CONF.read_text(),re.I|re.M): fail('Name in smb.conf bereits vergeben')
        import pwd
        try:
            user=pwd.getpwnam('markus')
            stirling=pwd.getpwnam('stirling')
        except KeyError: fail('Linux-Benutzer markus oder stirling fehlt')
        if preset in ('general','paperless'):
            directory=(BASE/'Paperless-Consume' if preset=='paperless' else BASE/name)
            owner=user
        else:
            directory=PIPELINE/PRESETS[preset]/name
            owner=stirling
        # Do not change ownership of an existing folder. Pipeline directories
        # are created only if absent and are never removed by this application.
        if action=='create' and directory.exists():
            fail('Zielordner existiert bereits; keine automatische Uebernahme')
        if action=='update' and entries[name].get('path')!=str(directory):
            fail('Pfadwechsel bestehender Freigaben nicht erlaubt: erst Freigabe entfernen, dann neu erstellen')
        if not directory.exists():
            parent=directory.parent
            if preset in ('general','paperless'):
                BASE.mkdir(mode=0o755,parents=True,exist_ok=True)
            elif not parent.is_dir() or parent.is_symlink():
                fail('Stirling-PDF-Zielverzeichnis existiert nicht')
            directory.mkdir(mode=0o2770)
            os.chown(directory,owner.pw_uid,owner.pw_gid)
            os.chmod(directory,0o2770)
        if directory.is_symlink(): fail('Symbolische Links sind nicht erlaubt')
        entries[name]={'path':str(directory),'browseable':'yes','read only':'no' if writable=='yes' else 'yes',
                       'valid users':(entries.get(name,{}).get('valid users','markus')),'force user':owner.pw_name,
                       'comment':('Paperless Consume' if preset=='paperless' else 'Verwaltet durch Samba Share Manager'),
                       'create mask':'0660','directory mask':'2770'}
        put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe gespeichert','path':str(directory)}))
    else:
        if name not in entries: fail('Freigabe nicht gefunden')
        del entries[name]; put(entries)
        print(json.dumps({'ok':True,'message':'Freigabe entfernt. Dateien bleiben erhalten.'}))

if __name__=='__main__': main()
