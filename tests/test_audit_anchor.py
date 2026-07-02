import sys
import os
import unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from audit_anchor import sha256_hex, record_hash, link_hash, build_chain, chain_head, verify_chain

class TestAuditAnchor(unittest.TestCase):
    def test_build_chain_determinism(self):
        records = [b'record1', b'record2', b'record3']
        chain1 = build_chain(records)
        chain2 = build_chain(records)
        self.assertEqual(chain1, chain2)

    def test_chain_structure(self):
        records = [b'record1', b'record2', b'record3']
        chain = build_chain(records)
        self.assertEqual(len(chain), len(records))
        for i, entry in enumerate(chain):
            self.assertEqual(entry['seq'], i + 1)
            if i == 0:
                self.assertEqual(entry['prev_hash'], '0' * 64)
            else:
                self.assertEqual(entry['prev_hash'], chain[i - 1]['entry_hash'])

    def test_verify_chain_intact(self):
        records = [b'record1', b'record2', b'record3']
        chain = build_chain(records)
        verified, reason = verify_chain(records, chain)
        self.assertTrue(verified)
        self.assertIn('intact', reason)

    def test_record_tamper(self):
        records = [b'record1', b'record2', b'record3']
        chain = build_chain(records)
        tampered_records = records.copy()
        tampered_records[1] = b'record2_tampered'
        verified, reason = verify_chain(tampered_records, chain)
        self.assertFalse(verified)
        self.assertIn('mismatch at seq 2', reason)

    def test_reorder_tamper(self):
        records = [b'record1', b'record2', b'record3']
        chain = build_chain(records)
        tampered_records = records.copy()
        tampered_records[0], tampered_records[1] = tampered_records[1], tampered_records[0]
        verified, reason = verify_chain(tampered_records, chain)
        self.assertFalse(verified)

    def test_truncation_length_mismatch(self):
        records = [b'record1', b'record2', b'record3']
        chain = build_chain(records)
        truncated_chain = chain[:-1]
        verified, reason = verify_chain(records, truncated_chain)
        self.assertFalse(verified)
        self.assertIn('mismatch in length', reason)

    def test_empty_log(self):
        chain = build_chain([])
        self.assertEqual(chain, [])
        self.assertEqual(chain_head(chain), '0' * 64)

    def test_single_record(self):
        record = [b'record1']
        chain = build_chain(record)
        self.assertEqual(len(chain), 1)
        self.assertEqual(chain[0]['prev_hash'], '0' * 64)

    def test_hash_sanity(self):
        record = b'record1'
        self.assertEqual(record_hash(record), sha256_hex(record))
        prev_hash = '0' * 64
        rec_hash = sha256_hex(record)
        self.assertEqual(link_hash(prev_hash, rec_hash), sha256_hex((prev_hash + rec_hash).encode()))

if __name__ == '__main__':
    unittest.main()
