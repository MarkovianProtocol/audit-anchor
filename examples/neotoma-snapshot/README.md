# Anchoring a Neotoma snapshot to Bitcoin (worked example)

[Neotoma](https://github.com/markmhendrickson/neotoma) gives agents a deterministic, versioned
state layer: observations reduce to a reproducible entity snapshot, and every field traces back
to the observation that set it. The one property that stops at the instance boundary is external
verifiability: a third party who did not run your Neotoma instance cannot prove a snapshot existed,
unaltered, at a claimed time, without trusting the operator.

This example closes that gap. It reduces the observations into the snapshot exactly as Neotoma's
`/get_entity_snapshot` does, canonicalizes the deterministic core (RFC 8785), hashes it to a root,
and anchors that root to Bitcoin with OpenTimestamps. Because Neotoma is deterministic, anyone
re-runs the reduction, gets the same root, and checks it against the chain. **No oracle, no trust in
the instance, verifiable offline.**

## The two Neotoma endpoints it uses

- `POST /list_observations` (or `POST /get_entity_snapshot`) — the inputs and the reduction.
- `POST /get_field_provenance` — optional; the field → observation map, carried into the receipt.

Everything the anchor needs is already in Neotoma's response. The anchor is additive: one root per
snapshot, opt-in, off the data path.

## Run it (offline, on the bundled sample)

```bash
pip install opentimestamps-client   # for the Bitcoin anchor + offline verify
python3 anchor.py                   # reduce -> canonical root -> stamp to Bitcoin -> receipt.json
python3 verify.py                   # re-derive the root and check it, trusting no one
```

`verify.py` prints `ALL CHECKS PASS` when the re-derived root matches the anchored root and the
OpenTimestamps proof resolves (pending, then Bitcoin-confirmed within ~an hour).

## What the sample demonstrates

The sample is a credit decision built from five observations by different agents. One of them,
`obs_05_backfilled`, has an early `observed_at` (14:05) but a late `created_at` (next day). Under
the bi-temporal cutoff (`created_at <= at_ingested`) it is **excluded**, so the snapshot correctly
reads `status = declined`, not the backfilled `approved`. The anchor captures exactly the state that
was knowable at ingestion time. Change one observation, and the re-derived root no longer matches.

## Against a real instance

```bash
export NEOTOMA_BEARER_TOKEN=...     # your instance token
curl -s -H "Authorization: Bearer $NEOTOMA_BEARER_TOKEN" -X POST \
     "$NEOTOMA_HOST/list_observations" -d '{"entity_id":"<entity_id>"}' > sample_observations.json
python3 anchor.py && python3 verify.py
```

The reduction here mirrors Neotoma's default `last_write` strategy. For entities using a
`highest_priority` merge strategy, swap the reducer to sort by `source_priority`; the anchor and
verify flow is unchanged.

Reference implementation of the produce/verify/tamper-detect cycle:
[github.com/MarkovianProtocol/audit-anchor](https://github.com/MarkovianProtocol/audit-anchor) ·
[markovianprotocol.com](https://markovianprotocol.com)

Apache-2.0.
