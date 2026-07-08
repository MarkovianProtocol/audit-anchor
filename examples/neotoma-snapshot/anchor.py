#!/usr/bin/env python3
"""Anchor a Neotoma entity snapshot to Bitcoin.

Reduce the observations into the deterministic snapshot core (exactly what /get_entity_snapshot
computes), canonicalize it (RFC 8785), hash it to a root, and stamp that root directly to Bitcoin
with OpenTimestamps. Writes receipt.json + snapshot_core.json. No operator, no api server.

Against a real instance you would fetch the inputs first:
    curl -H "Authorization: Bearer $NEOTOMA_BEARER_TOKEN" -X POST $HOST/list_observations \
         -d '{"entity_id":"credit_decision:app-4471"}'
then anchor the root of the reduced snapshot. Here we use sample_observations.json so the whole
thing runs offline.
"""
import json, os, base64, subprocess, tempfile, shutil
from neotoma_snapshot import reduce_snapshot, snapshot_root

D = os.path.dirname(os.path.abspath(__file__))
AT = "2026-07-01T23:59:59Z"
AT_INGESTED = "2026-07-01T23:59:59Z"

def ots_bin():
    for c in (os.environ.get("OTS_BIN"), shutil.which("ots"), os.path.expanduser("~/neo_env/bin/ots")):
        if c and os.path.exists(c):
            return c
    return None

obs = json.load(open(os.path.join(D, "sample_observations.json")))
core = reduce_snapshot(obs, AT, AT_INGESTED)
root = snapshot_root(core)

ots_b64 = None
b = ots_bin()
if b:
    with tempfile.TemporaryDirectory() as td:
        f = os.path.join(td, "root")
        open(f, "wb").write(root.encode())
        subprocess.run([b, "stamp", f], capture_output=True, timeout=90)
        if os.path.exists(f + ".ots"):
            ots_b64 = base64.b64encode(open(f + ".ots", "rb").read()).decode()

receipt = {
    "kind": "neotoma-snapshot-anchor/v1",
    "source": "Neotoma /get_entity_snapshot (deterministic bi-temporal reduction)",
    "entity_id": core["entity_id"],
    "at": AT, "at_ingested": AT_INGESTED,
    "observation_count": core["observation_count"],
    "snapshot_root": root,
    "canonicalization": "RFC 8785 (JCS) over the deterministic snapshot core; wall-clock computed_at excluded",
    "anchor": {"type": "opentimestamps", "ots_b64": ots_b64, "status": "submitted" if ots_b64 else "no-client"},
}
json.dump(receipt, open(os.path.join(D, "receipt.json"), "w"), indent=2)
json.dump(core, open(os.path.join(D, "snapshot_core.json"), "w"), indent=2)
print(f"snapshot_root = {root}")
print(f"observations bounded = {core['observation_count']} (obs_05_backfilled excluded: created_at after cutoff)")
print(f"snapshot.status   = {core['snapshot'].get('status')}   (declined, NOT the backfilled 'approved')")
print(f"opentimestamps    = {'stamped, pending Bitcoin' if ots_b64 else 'client not found'}")
