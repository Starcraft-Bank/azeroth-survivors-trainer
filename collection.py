"""Standalone trainer collection grant, explicitly authorized for public release.

Uses the supported game's own authenticated save format, independently encoded
with Python's standard HMAC/SHA-1 primitives. No bundled save or personal data.
The game must be closed before committing and restarted to load the result.
"""
from pathlib import Path
import base64
import ctypes
from ctypes import wintypes
import hashlib
import hmac
import json
import os
import struct
import sys
import time
import uuid

GAME_SHA256 = '522e1c831b3b4627875a28a1030368ef9d2e7f98c5606c34cb30448d3b7d776e'
SUPPORTED_GAMES = {
    '5dd6819d836748ccf809ab76fe6509c9ee793e087939b5d036c430d835a14e63': ((118051856, 118051872, 118051888, 103573552), (118051904, 118051920, 118051936, 103259392)),
    GAME_SHA256: ((116857568,116857584,116857600,102359808), (116857616,116857632,116857648,102326976)),
    'ec3a5b15fa39fed63ce4516c4fc159bdac92691ca44f88befc849010338d14f7':
        ((117179120,117179136,117179152,102392848), (117179168,117179184,117179200,102451824)),
    'de7147a2a3a01b4fb84f3a7f036bc940f9e7d4fdfc42a7fdb79f3f1b2bd798be':
        ((117223616,117223632,117223648,102485152), (117223664,117223680,117223696,102484992)),
    '3ef9d74c30bb6b435d739b3d960c8535486836c540e0d8c20f98549a6f1dcbbb':
        ((121504720,121504736,121504752,102958656), (121504768,121504784,121504800,102960240)),
    '8829953418a4d996cc5287f0e9fad25407ca30ceb64d105a4f57833caef78016':
        ((118002672,118002688,118002704,103410464), (118002720,118002736,118002752,103333616)),
    'e8ff033544095e81d74087ff400d50286b26af02291e649f4c5e4d76cbcf8863':
        ((118007280,118007296,118007312,103464544), (118007328,118007344,118007360,103334224)),
}
CATALOG_VERSIONS = {
    '5dd6819d836748ccf809ab76fe6509c9ee793e087939b5d036c430d835a14e63': '0.130.0',  # Catalog identities and native reload verified for 0.131.0.
    GAME_SHA256: '0.120.5',
    'ec3a5b15fa39fed63ce4516c4fc159bdac92691ca44f88befc849010338d14f7': '0.122.0',
    'de7147a2a3a01b4fb84f3a7f036bc940f9e7d4fdfc42a7fdb79f3f1b2bd798be': '0.123.0',
    '3ef9d74c30bb6b435d739b3d960c8535486836c540e0d8c20f98549a6f1dcbbb': '0.127.0',
    '8829953418a4d996cc5287f0e9fad25407ca30ceb64d105a4f57833caef78016': '0.130.0',
    # The 0.130.1 racial balance hotfix retains the verified 0.130.0 unlock catalog.
    'e8ff033544095e81d74087ff400d50286b26af02291e649f4c5e4d76cbcf8863': '0.130.0',
}
ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
CATALOG = ROOT / 'collection-catalog.json'

def catalog_for_version(version):
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    overrides = catalog.pop('versions', {})
    if version != catalog['gameVersion']:
        if version not in overrides:raise ValueError('No verified collection catalog for this game version.')
        catalog.update(overrides[version])
    return catalog

def _key(exe, with_catalog=False):
    image = Path(exe).read_bytes()
    digest = hashlib.sha256(image).hexdigest()
    offsets = SUPPORTED_GAMES.get(digest)
    if offsets is None:
        raise ValueError('Unlock supports the verified native 0.120.5, 0.122.0, 0.123.0, 0.127.0, 0.130.0 and 0.130.1 builds only.')
    # Observed native HMAC inner/outer pad loads, exact artifact file offsets.
    inner = b''.join(image[n:n+16] for n in offsets[0])
    outer = b''.join(image[n:n+16] for n in offsets[1])
    key = bytes(v ^ 0x36 for v in inner)
    if key != bytes(v ^ 0x5c for v in outer):
        raise ValueError('Native save key validation failed.')
    return (key, catalog_for_version(CATALOG_VERSIONS[digest])) if with_catalog else key

def _crypt(data, nonce, key):
    output = bytearray()
    for offset in range(0, len(data), 20):
        pad = hmac.digest(key, b'ks' + nonce + struct.pack('<Q', offset // 20), 'sha1')
        output.extend(a ^ b for a, b in zip(data[offset:offset+20], pad))
    return bytes(output)

def decode(payload, key):
    if not payload.startswith(b'RSE1:') or not 32 <= len(payload) <= 4*1024*1024:
        raise ValueError('Unrecognized native save; no changes made.')
    raw = base64.b64decode(payload[5:].strip(), validate=True)
    if len(raw) < 36:
        raise ValueError('Truncated native save.')
    nonce, encrypted, tag = raw[:16], raw[16:-20], raw[-20:]
    if not hmac.compare_digest(tag, hmac.digest(key, b'tag'+nonce+encrypted, 'sha1')):
        raise ValueError('Native save authentication failed; no changes made.')
    return _crypt(encrypted, nonce, key).decode('utf-8')

def encode(text, key):
    nonce = os.urandom(16)
    encrypted = _crypt(text.encode('utf-8'), nonce, key)
    return b'RSE1:' + base64.b64encode(nonce+encrypted+hmac.digest(key,b'tag'+nonce+encrypted,'sha1'))

def default_save():
    override = os.environ.get('WOW_ROGUE_SAVE')
    return Path(override) if override else Path(os.environ['APPDATA'])/'wenilla-rogue'/'characters.txt'

def game_processes():
    """Fail closed if any native game remains open and could overwrite its save."""
    class Entry(ctypes.Structure):
        _fields_ = [('size',wintypes.DWORD),('usage',wintypes.DWORD),('pid',wintypes.DWORD),
                    ('heap',ctypes.c_size_t),('module',wintypes.DWORD),('threads',wintypes.DWORD),
                    ('parent',wintypes.DWORD),('priority',wintypes.LONG),('flags',wintypes.DWORD),
                    ('exe',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError('Could not verify that the game is closed.')
    found=[]; entry=Entry(); entry.size=ctypes.sizeof(entry)
    try:
        more=kernel.Process32FirstW(handle,ctypes.byref(entry))
        if not more:raise OSError('Could not enumerate game processes safely.')
        while more:
            if entry.exe.casefold()=='azerothsurvivors.exe':found.append(entry.pid)
            more=kernel.Process32NextW(handle,ctypes.byref(entry))
        if ctypes.get_last_error()!=18:raise OSError('Process enumeration was incomplete.')
    finally:kernel.CloseHandle(handle)
    return found

def grant_text(text, catalog=None, timestamp=None):
    catalog = catalog or json.loads(CATALOG.read_text(encoding='utf-8'))
    timestamp = int(time.time()) if timestamp is None else timestamp
    lines=text.splitlines()
    if not any(line.startswith('pick|') for line in lines):
        raise ValueError('Save has no character selection record.')
    def get(kind, cls=None):
        prefix=kind+'|' if cls is None else kind+'|'+str(cls)+'|'
        matches=[line for line in lines if line.startswith(prefix)]
        if len(matches)>1:raise ValueError('Duplicate save records: '+prefix)
        return matches[0].split('|') if matches else None
    def put(kind, value, cls=None):
        prefix=kind+'|' if cls is None else kind+'|'+str(cls)+'|'
        lines[:]=[line for line in lines if not line.startswith(prefix)]
        lines.append(prefix+value)
    def union(kind, values, cls=None):
        old=get(kind,cls); existing=old[-1].split(',') if old and old[-1] else []
        put(kind,','.join(sorted(set(existing)|{str(v) for v in values})),cls)
    def pairs(kind, values, separator='=', keep_existing=False):
        old=get(kind); result={}
        for entry in (old[-1].split(',') if old and old[-1] else []):
            key, sep, value=entry.rpartition(separator)
            if not sep:raise ValueError('Invalid '+kind+' entry.')
            result[key]=int(value)
        for key,value in values.items():
            if keep_existing and key in result:continue
            result[key]=max(result.get(key,0),value)
        put(kind,','.join(k+separator+str(v) for k,v in sorted(result.items())))
    union('ach',catalog['achievements'])
    pairs('achat',{key:timestamp for key in catalog['achievements']},keep_existing=True)
    union('items',catalog['items'])
    union('tabard',catalog['purchasedTabards'])
    union('races',catalog['races'])
    pairs('perk',catalog['perks'],':')
    pairs('seen',catalog['seen'])
    union('coopbeat',catalog['zones'])
    for cls in catalog['classes']:
        put('open',catalog['zones'][-1],cls)
        union('beat',catalog['zones'],cls)
        old=get('talent',cls)
        if old:
            if len(old)!=4:raise ValueError('Invalid talent record.')
            put('talent',str(max(int(old[2]),23205))+'|'+old[3],cls)
        else:put('talent','23205|',cls)
    # Companions and appearances are achievement-gated; pets/hero/look record
    # currently equipped choices, so preserve them instead of equipping all.
    return '\n'.join(lines)+'\n'

def unlock_save(game_exe, save_path=None, backup_dir=None):
    if game_processes():raise RuntimeError('Close every Azeroth Survivors game window before unlocking.')
    source=Path(save_path) if save_path is not None else default_save()
    if not source.is_file():raise FileNotFoundError('Create a character in the native game first, then try again.')
    original=source.read_bytes();key,catalog=_key(game_exe,with_catalog=True)
    before=decode(original,key);after=grant_text(before,catalog)
    result=encode(after,key)
    if decode(result,key)!=after:raise RuntimeError('Save verification failed; original kept.')
    backup_root=Path(backup_dir) if backup_dir is not None else Path(os.environ['LOCALAPPDATA'])/'AzerothSurvivorsTrainerNative'/'Collection Backups'
    backup_root.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(original).hexdigest()
    backup=backup_root/('before-unlock-'+digest+'.txt')
    if not backup.exists():
        with backup.open('xb') as stream:stream.write(original);stream.flush();os.fsync(stream.fileno())
    if backup.read_bytes()!=original:raise RuntimeError('Backup verification failed; original kept.')
    temporary=source.with_name(source.name+'.trainer-'+uuid.uuid4().hex+'.tmp')
    try:
        with temporary.open('xb') as stream:stream.write(result);stream.flush();os.fsync(stream.fileno())
        if decode(temporary.read_bytes(),key)!=after:raise RuntimeError('Temporary save verification failed.')
        if game_processes() or source.read_bytes()!=original:raise RuntimeError('The game or save changed; retry after closing the game.')
        os.replace(temporary,source)
        if source.read_bytes()!=result:raise RuntimeError('Save readback failed; verified backup is at '+str(backup))
    finally:
        if temporary.exists():temporary.unlink()
    return {'backup':str(backup),'save':str(source),'originalSha256':digest,
            'newSha256':hashlib.sha256(result).hexdigest(),'message':'Collection unlocked. Restart the native game.'}
