#!/usr/bin/env python3
"""
audit_anchor.py - Anchor any audit trail tool: provides tamper-evidence, timestamping, and operator-independent verifiability of a record,
it does NOT capture events, does NOT judge whether logged content is correct, and is NOT a compliance system,
maps to EU AI Act Article 12, FDA 21 CFR Part 11 section 11.10(e), SEC 17a-4(f).
"""

import json
import hashlib
import urllib.request
import argparse
import sys
import os

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
        entry = {'seq': i + 1, 'record_sha256': rec_hash, 'prev_hash': prev_hash, 'entry_hash': entry_hash}
        chain.append(entry)
        prev_hash = entry_hash
    return chain

def chain_head(chain):
    if not chain:
        return '0' * 64
    return chain[-1]['entry_hash']

def verify_chain(records, chain):
    recomputed_chain = build_chain(records)
    if len(recomputed_chain) != len(chain):
        return False, f'mismatch in length: {len(recomputed_chain)} vs {len(chain)}'
    for i in range(len(chain)):
        if recomputed_chain[i]['record_sha256'] != chain[i]['record_sha256']:
            return False, f'mismatch at seq {i + 1}: record_sha256'
        if recomputed_chain[i]['prev_hash'] != chain[i]['prev_hash']:
            return False, f'mismatch at seq {i + 1}: prev_hash'
        if recomputed_chain[i]['entry_hash'] != chain[i]['entry_hash']:
            return False, f'mismatch at seq {i + 1}: entry_hash'
    return True, f'intact, {len(chain)} entries'

def anchor_head(head, label):
    try:
        data = {'data_hash': head, 'label': label}
        req = urllib.request.Request('https://api.quantsynth.net/stamp', json.dumps(data).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'python-httpx/0.27.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            r = json.loads(response.read())
        return {
            'ok': r.get('ok', False),
            'merkle_root': r.get('merkle_root'),
            'zk_commitment': r.get('zk_commitment'),
            'markovian_block': r.get('block_height'),
            'stamped_at': r.get('stamped_at'),
            'verify_url': r.get('verify_url'),
            'ots_url': (r.get('verify_url') + '.ots') if r.get('verify_url') else None,
        }
    except Exception as e:
        return {'error': str(e)}

def write_manifest(path, manifest):
    with open(path, 'w') as f:
        json.dump(manifest, f)

def read_manifest(path):
    with open(path, 'r') as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    subparsers = ap.add_subparsers(dest='command')
    anchor_parser = subparsers.add_parser('anchor')
    anchor_parser.add_argument('logfile', help='path to newline-delimited log')
    anchor_parser.add_argument('--label', default='audit trail', help='label for the anchor')
    anchor_parser.add_argument('--out', default='anchor.json', help='output manifest file')
    verify_parser = subparsers.add_parser('verify')
    verify_parser.add_argument('logfile', help='path to newline-delimited log')
    verify_parser.add_argument('--anchor', default='anchor.json', help='input manifest file')
    ap.add_argument('--selftest', action='store_true', help='run self-test')
    a = ap.parse_args()
    if a.selftest:
        sample_log = [b'record1', b'record2', b'record3', b'record4', b'record5']
        chain = build_chain(sample_log)
        assert verify_chain(sample_log, chain) == (True, 'intact, 5 entries'), 'chain is not intact'
        chain2 = build_chain(sample_log)
        assert json.dumps(chain, sort_keys=True) == json.dumps(chain2, sort_keys=True), 'chain is not deterministic'
        tampered_log = sample_log.copy()
        tampered_log[2] = b'record3_tampered'
        tampered_chain = build_chain(tampered_log)
        assert verify_chain(tampered_log, chain) != (True, 'intact, 5 entries'), 'tampered chain is still intact'
        assert chain_head(chain) != chain_head(tampered_chain), 'tampered chain has the same head'
        reordered_log = sample_log.copy()
        reordered_log[1], reordered_log[2] = reordered_log[2], reordered_log[1]
        reordered_chain = build_chain(reordered_log)
        assert verify_chain(reordered_log, chain) != (True, 'intact, 5 entries'), 'reordered chain is still intact'
        print('SELFTEST OK')
        sys.exit(0)
    if a.command == 'anchor':
        with open(a.logfile, 'rb') as f:
            records = [line.rstrip(b'\n') for line in f.readlines() if line.rstrip(b'\n')]
        chain = build_chain(records)
        head = chain_head(chain)
        anchor = anchor_head(head, a.label)
        manifest = {'version': '1', 'entries': len(chain), 'chain_head': head, 'anchor': anchor, 'chain': chain}
        write_manifest(a.out, manifest)
        print(f'Committed {len(chain)} entries. chain_head={head}')
        print(f'merkle_root={anchor.get("merkle_root", anchor.get("error"))}  markovian_block={anchor.get("markovian_block")}')
        print(f'verify_url={anchor.get("verify_url")}')
    elif a.command == 'verify':
        with open(a.logfile, 'rb') as f:
            records = [line.rstrip(b'\n') for line in f.readlines() if line.rstrip(b'\n')]
        manifest = read_manifest(a.anchor)
        chain = manifest['chain']
        verified, reason = verify_chain(records, chain)
        print(f'Verification: {"PASS" if verified else "FAIL"} - {reason}')
        recomputed_head = chain_head(build_chain(records))
        if verified and recomputed_head == manifest['chain_head']:
            print('Chain head matches the anchored head')
            print('Tier 1 (local): the audit trail is internally consistent and the head is unchanged. This needs nothing and nobody.')
            verify_url = manifest['anchor'].get('verify_url')
            if verify_url:
                print(f'Tier 2 (external anchor): confirm the head is recorded on the Markovian chain at {verify_url}')
                print('The operator cannot forge or rewrite that record.')
                ots_url = manifest['anchor'].get('ots_url')
                if ots_url:
                    print(f'Tier 3 (Bitcoin, matures): fetch {ots_url} and check it with the OpenTimestamps client. Once it carries a Bitcoin attestation, this needs nothing from Markovian.')
            sys.exit(0)
        else:
            print('Chain head does not match the anchored head')
            sys.exit(1)

if __name__ == '__main__':
    main()
