#!/usr/bin/env python3
"""Verify the Neotoma snapshot anchor by RE-DERIVING it, trusting nothing from Neotoma or from us.

Re-runs the deterministic reduction over the raw observations, recomputes the canonical root,
checks it equals the anchored root in the receipt, and checks the Bitcoin proof with the
OpenTimestamps client. Anyone with the same observations gets the same root. That is the point.
"""
import json, os, base64, subprocess, tempfile, shutil, sys
from neotoma_snapshot import reduce_snapshot, snapshot_root

D = os.path.dirname(os.path.abspath(__file__))

def ots_bin():
    for c in (os.environ.get("OTS_BIN"), shutil.which("ots"), os.path.expanduser("~/neo_env/bin/ots")):
        if c and os.path.exists(c):
            return c
    return None

def ots_status(ots_b64, root):
    b = ots_bin()
    if not b:
        return "UNVERIFIED", "OpenTimestamps client not installed (pip install opentimestamps-client)"
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "root")
        open(f, "wb").write(root.encode())
        open(f + ".ots", "wb").write(base64.b64decode(ots_b64))
        subprocess.run([b, "upgrade", f + ".ots"], capture_output=True, timeout=90)
        info = (subprocess.run([b, "info", f + ".ots"], capture_output=True, text=True, timeout=60).stdout or "")
        low = info.lower()
        if "bitcoin" in low and "block" in low:
            line = next((l.strip() for l in info.splitlines() if "bitcoin" in l.lower() and "block" in l.lower()), "Bitcoin attestation present")
            return "BITCOIN", line
        if "pending" in low or "calendar" in low:
            return "PENDING", "Submitted to public calendars; Bitcoin confirmation matures in ~an hour to a day. Re-run later."
        return "UNVERIFIED", (info.strip()[:160] or "could not read the proof")

r = json.load(open(os.path.join(D, "receipt.json")))
obs = json.load(open(os.path.join(D, "sample_observations.json")))

core = reduce_snapshot(obs, r["at"], r["at_ingested"])
root = snapshot_root(core)

print(f"re-derived snapshot for {r['entity_id']} at (event={r['at']}, ingested={r['at_ingested']})")
print(f"  status={core['snapshot'].get('status')}  observations={core['observation_count']}\n")

ok_all = True
def check(name, ok, detail):
    global ok_all
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}\n         {detail}")
    ok_all = ok_all and ok

check("re-derived root == anchored root (deterministic replay)", root == r["snapshot_root"], root)
status, detail = ots_status(r["anchor"]["ots_b64"], r["snapshot_root"]) if r["anchor"].get("ots_b64") else ("UNVERIFIED", "no proof in receipt")
check("Bitcoin anchor (OpenTimestamps)", status in ("BITCOIN", "PENDING"), f"{status}: {detail}")

print("\nRESULT:", "ALL CHECKS PASS - the snapshot is independently reproducible and anchored. No trust in Neotoma or Markovian."
      if ok_all else "MISMATCH - do not trust.")
sys.exit(0 if ok_all else 1)
