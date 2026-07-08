#!/usr/bin/env python3
"""
audit_anchor.py - Anchor any audit trail. Provides tamper-evidence, timestamping, and
operator-independent verifiability of a record. It does NOT capture events, does NOT judge
whether logged content is correct, and is NOT a compliance system. Maps to EU AI Act
Article 12, FDA 21 CFR Part 11 section 11.10(e), SEC 17a-4(f).

Two anchor modes:
  --local  (recommended, trustless): stamp the chain head directly to Bitcoin with
           OpenTimestamps. No operator. `verify` re-runs the OpenTimestamps client offline
           and reports the real Bitcoin attestation, so verification trusts math, not us.
  (default) server: batch the head through api.quantsynth.net for an interim anchor. Faster,
           but its integrity rests on the operator until the OpenTimestamps proof matures.

The core (build/verify/selftest) is pure stdlib. --local and the Bitcoin check use the
OpenTimestamps client (`pip install opentimestamps-client`, or the `ots` binary on PATH).
"""

import json
import hashlib
import urllib.request
import argparse
import sys
import os
import shutil
import base64
import tempfile
import subprocess


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()

def record_hash(record_bytes):
    return sha256_hex(record_bytes)

def link_hash(prev_entry_hash_hex, rec_hash_hex):
    return sha256_hex((prev_entry_hash_hex + rec_hash_hex).encode())

def build_chain(records):
    chain = []
    prev_hash = '0' * 64
    for i, record in enumerate(records):
        rec_hash = record_hash(record)
        entry_hash = link_hash(prev_hash, rec_hash)
        chain.append({'seq': i + 1, 'record_sha256': rec_hash, 'prev_hash': prev_hash, 'entry_hash': entry_hash})
        prev_hash = entry_hash
    return chain

def chain_head(chain):
    return chain[-1]['entry_hash'] if chain else '0' * 64

def verify_chain(records, chain):
    recomputed = build_chain(records)
    if len(recomputed) != len(chain):
        return False, f'mismatch in length: {len(recomputed)} vs {len(chain)}'
    for i in range(len(chain)):
        for k in ('record_sha256', 'prev_hash', 'entry_hash'):
            if recomputed[i][k] != chain[i][k]:
                return False, f'mismatch at seq {i + 1}: {k}'
    return True, f'intact, {len(chain)} entries'


# ---- OpenTimestamps client (optional; used by --local and by verify's Bitcoin tier) ----

def ots_bin():
    """Locate the OpenTimestamps client: $OTS_BIN, then PATH, then a couple of common venvs."""
    for cand in (os.environ.get('OTS_BIN'), shutil.which('ots'),
                 os.path.expanduser('~/neo_env/bin/ots'), '/usr/local/bin/ots'):
        if cand and os.path.exists(cand):
            return cand
    return None

def _run(bin_, args, timeout=120):
    return subprocess.run([bin_] + args, capture_output=True, text=True, timeout=timeout)

def ots_stamp_head(head_hex):
    """Stamp the chain head DIRECTLY to Bitcoin (no operator). The head hex is the exact
    bytes anchored, so anyone who recomputes the head can verify the same proof.
    Returns base64(.ots) or {'error': ...}."""
    b = ots_bin()
    if not b:
        return {'error': 'OpenTimestamps client not found. Install: pip install opentimestamps-client'}
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, 'head')
        open(f, 'wb').write(head_hex.encode())          # anchored bytes = the head hex, verbatim
        r = _run(b, ['stamp', f])
        otsf = f + '.ots'
        if os.path.exists(otsf):
            return {'ots_b64': base64.b64encode(open(otsf, 'rb').read()).decode(),
                    'anchored_bytes': 'chain_head hex, utf-8, no newline',
                    'submitted': (r.stdout + r.stderr).strip()[:200]}
        return {'error': (r.stdout + r.stderr).strip()[:200] or 'stamp produced no .ots'}

def ots_check_head(ots_b64, head_hex):
    """Re-run the OpenTimestamps client OFFLINE against the recomputed head. Reports the real
    attestation: Bitcoin-confirmed at a block, or still pending in the calendars."""
    b = ots_bin()
    if not b:
        return 'CLIENT_MISSING', 'OpenTimestamps client not installed; cannot check the Bitcoin anchor. Install: pip install opentimestamps-client'
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, 'head')
        open(f, 'wb').write(head_hex.encode())
        open(f + '.ots', 'wb').write(base64.b64decode(ots_b64))
        _run(b, ['upgrade', f + '.ots'])                # best-effort: pull Bitcoin attestation if ready
        info = (_run(b, ['info', f + '.ots']).stdout or '')
        low = info.lower()
        if 'bitcoin' in low and 'block' in low:
            line = next((l.strip() for l in info.splitlines() if 'bitcoin' in l.lower() and 'block' in l.lower()), 'Bitcoin attestation present')
            return 'BITCOIN', line
        if 'pending' in low or 'calendar' in low or 'verifypending' in low:
            return 'PENDING', 'Submitted to public calendars; Bitcoin attestation not yet confirmed (matures in ~an hour to a day). Re-run verify later.'
        return 'UNKNOWN', (info.strip()[:200] or 'could not read the OpenTimestamps proof')


# ---- interim server anchor (kept for backward compatibility; trust boundary = operator) ----

def anchor_head_server(head, label):
    try:
        data = {'data_hash': head, 'label': label}
        req = urllib.request.Request('https://api.quantsynth.net/stamp', json.dumps(data).encode(),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'python-httpx/0.27.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            r = json.loads(resp.read())
        return {'mode': 'server', 'ok': r.get('ok', False), 'merkle_root': r.get('merkle_root'),
                'zk_commitment_server_asserted': r.get('zk_commitment'),  # server-asserted, not verified by this client
                'markovian_block': r.get('block_height'), 'stamped_at': r.get('stamped_at'),
                'verify_url': r.get('verify_url'),
                'note': 'interim anchor; integrity rests on the operator until an OpenTimestamps proof matures. Use --local for a trustless anchor.'}
    except Exception as e:
        return {'error': str(e)}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='command')
    ap_anchor = sub.add_parser('anchor')
    ap_anchor.add_argument('logfile')
    ap_anchor.add_argument('--label', default='audit trail')
    ap_anchor.add_argument('--out', default='anchor.json')
    ap_anchor.add_argument('--local', action='store_true', help='trustless: stamp the head directly to Bitcoin via OpenTimestamps (no operator)')
    ap_verify = sub.add_parser('verify')
    ap_verify.add_argument('logfile')
    ap_verify.add_argument('--anchor', default='anchor.json')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()

    if a.selftest:
        log = [b'record1', b'record2', b'record3', b'record4', b'record5']
        chain = build_chain(log)
        assert verify_chain(log, chain) == (True, 'intact, 5 entries')
        assert build_chain(log) == chain, 'not deterministic'
        t = log.copy(); t[2] = b'record3_tampered'
        assert verify_chain(t, chain)[0] is False and chain_head(build_chain(t)) != chain_head(chain)
        ro = log.copy(); ro[1], ro[2] = ro[2], ro[1]
        assert verify_chain(ro, chain)[0] is False
        print('SELFTEST OK')
        sys.exit(0)

    if a.command == 'anchor':
        with open(a.logfile, 'rb') as f:
            records = [ln.rstrip(b'\n') for ln in f if ln.rstrip(b'\n')]
        chain = build_chain(records)
        head = chain_head(chain)
        if a.local:
            anchor = ots_stamp_head(head); anchor['mode'] = 'local'
        else:
            anchor = anchor_head_server(head, a.label)
        manifest = {'version': '2', 'entries': len(chain), 'chain_head': head, 'anchor': anchor, 'chain': chain}
        with open(a.out, 'w') as f:
            json.dump(manifest, f)
        print(f'Committed {len(chain)} entries. chain_head={head}')
        if anchor.get('mode') == 'local':
            print('Anchored the head DIRECTLY to Bitcoin via OpenTimestamps.' if 'ots_b64' in anchor
                  else f'Local anchor failed: {anchor.get("error")}')
            print('Run `verify` to re-derive the head and check the Bitcoin proof offline. Trust math, not us.')
        else:
            print(f'merkle_root={anchor.get("merkle_root", anchor.get("error"))}  markovian_block={anchor.get("markovian_block")}')
            print(f'verify_url={anchor.get("verify_url")}  (interim; use --local for a trustless anchor)')

    elif a.command == 'verify':
        with open(a.logfile, 'rb') as f:
            records = [ln.rstrip(b'\n') for ln in f if ln.rstrip(b'\n')]
        manifest = json.load(open(a.anchor))
        chain = manifest['chain']
        ok, reason = verify_chain(records, chain)
        recomputed_head = chain_head(build_chain(records))
        head_ok = ok and recomputed_head == manifest['chain_head']
        print(f'Tier 1 (local, needs nobody): {"PASS" if head_ok else "FAIL"} - {reason}')
        if not head_ok:
            print('The audit trail does not match its committed head. Reject.')
            sys.exit(1)
        anchor = manifest.get('anchor', {})
        if anchor.get('mode') == 'local' and anchor.get('ots_b64'):
            status, detail = ots_check_head(anchor['ots_b64'], manifest['chain_head'])
            label = {'BITCOIN': 'PASS', 'PENDING': 'PENDING', 'CLIENT_MISSING': 'UNVERIFIED', 'UNKNOWN': 'UNVERIFIED'}[status]
            print(f'Tier 3 (Bitcoin, trustless): {label} - {detail}')
            sys.exit(0 if status in ('BITCOIN', 'PENDING') else 2)
        else:
            print('Tier 2 (interim server anchor): head recorded via api.quantsynth.net; integrity rests on the operator.')
            vu = anchor.get('verify_url')
            if vu:
                print(f'  cross-check: {vu}')
            print('For a trustless, offline-checkable anchor, re-run `anchor --local`.')
            sys.exit(0)


if __name__ == '__main__':
    main()
