#!/usr/bin/env bash
# Recover only the Samba Share Manager GUI administrator login.
# SMB accounts, shares, and documents are never modified.
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Als root starten" >&2; exit 1; }
AUTH=/etc/samba-share-manager/auth.json
[[ -f "$AUTH" ]] || { echo "GUI noch nicht installiert: $AUTH fehlt" >&2; exit 1; }
python3 - <<'PY'
import hashlib,json,os,secrets,tempfile
from pathlib import Path
p=Path('/etc/samba-share-manager/auth.json')
password=secrets.token_urlsafe(18)
salt=secrets.token_bytes(16)
record={'salt':salt.hex(),'rounds':600000,'digest':hashlib.pbkdf2_hmac('sha256',password.encode(),salt,600000).hex(),'must_change':True}
stat=p.stat()
fd,temp=tempfile.mkstemp(prefix='.auth-reset-',dir=str(p.parent))
try:
    with os.fdopen(fd,'w') as stream:
        json.dump(record,stream)
        stream.flush();os.fsync(stream.fileno())
    os.chown(temp,stat.st_uid,stat.st_gid)
    os.chmod(temp,0o640)
    os.replace(temp,p)
finally:
    if os.path.exists(temp):os.unlink(temp)
print('Benutzer: admin')
print('Neues Einmalpasswort: '+password)
print('Beim ersten Login direkt aendern (mindestens 12 Zeichen).')
PY
systemctl restart samba-share-manager.service
