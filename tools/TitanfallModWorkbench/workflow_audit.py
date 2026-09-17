"""Read-only delivery audit. No game launch or inferred runtime acceptance."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path


def audit(source):
    source = Path(source)
    issues = []
    if source.is_dir():
        files = {p.relative_to(source).as_posix(): p.read_bytes()
                 for p in source.rglob('*') if p.is_file()}
    else:
        with zipfile.ZipFile(source) as z:
            bad = z.testzip()
            if bad:
                raise ValueError('ZIP CRC failure: ' + bad)
            names = [n for n in z.namelist() if not n.endswith('/')]
            manifests = [n for n in names if n == 'mod.json' or n.endswith('/mod.json')]
            if len(manifests) != 1:
                raise ValueError('Expected exactly one mod.json')
            prefix = manifests[0][:-len('mod.json')]
            if any(not n.startswith(prefix) or '..' in n.split('/') for n in names):
                raise ValueError('Unexpected archive layout')
            if len(names) != len(set(names)):
                raise ValueError('Duplicate archive entries')
            files = {n[len(prefix):]: z.read(n) for n in names}
    meta = json.loads(files['mod.json'].decode('utf-8-sig'))
    if meta.get('LoadPriority') != 0:
        issues.append('LoadPriority differs from project requirement 0')
    patches = {n: b.decode('utf-8-sig') for n,b in files.items()
               if n.startswith('keyvalues/') and n.endswith('mp_weapon_car.txt')}
    ui = {'ammo': 'NOT_VERIFIED', 'proScreen': 'NOT_VERIFIED'}
    for text in patches.values():
        text = re.sub(r'//[^\n]*', '', text)
        if 'ui8_enable' in text or 'pro_screen' in text:
            ui['proScreen'] = 'CONFIG_PRESENT_NOT_RUNTIME_VERIFIED'
        if 'weapon_ammo' in text and 'car_smg_rui_' in text:
            ui['ammo'] = 'CONFIG_PRESENT_GEOMETRY_AND_MERGE_NOT_VERIFIED'
    if patches and ui['ammo'] == 'NOT_VERIFIED':
        issues.append('Ammo UI is inherited/unverified; ui8/pro_screen is not proof of ammo display')
    particles = [n for n in files if n.endswith('.pcf')]
    manifests = [n for n in files if n.lower().endswith('particles_manifest.txt')]
    if manifests:
        issues.append('Global particle manifest override requires review against stock manifest')
    glow = [n for n in files if n.endswith('.vmt') and
            any(k in files[n].lower() for k in [b'unlit', b'selfillum'])]
    if glow or particles:
        issues.append('Glow/particle resources exist; rendered visibility is not verified')
    return {'name':meta.get('Name'), 'version':meta.get('Version'),
            'scope':'delivery inventory and configuration only',
            'runtimeStatus':'NOT_TESTED', 'releaseAcceptance':'PENDING',
            'loadPriority':meta.get('LoadPriority'), 'ui':ui,
            'pcfFiles':particles, 'emissiveMaterialFiles':glow,
            'issues':issues, 'sha256':{n:hashlib.sha256(b).hexdigest() for n,b in files.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = audit(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Report saved; runtime acceptance remains PENDING: ' + str(args.output))
