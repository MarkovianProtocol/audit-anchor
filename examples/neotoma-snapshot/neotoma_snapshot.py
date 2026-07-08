#!/usr/bin/env python3
"""Deterministic reduction of Neotoma observations into a snapshot core, matching Neotoma's
default bi-temporal, last-write model. This is the function anyone re-runs to reproduce the
snapshot Markovian anchored. No wall-clock, no randomness, no operator: pure function of inputs.
"""
import json
import hashlib


def jcs(o):
    """RFC 8785 (JCS) canonical bytes."""
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def reduce_snapshot(observations, at, at_ingested):
    """Reconstruct the entity snapshot from observations, exactly as Neotoma's
    /get_entity_snapshot does under the default reducer:

      - bi-temporal cutoff: keep observations with observed_at <= at AND created_at <= at_ingested
        (the created_at bound excludes backfilled/late-arriving rows, preventing look-ahead leaks)
      - last_write per field: order by (observed_at, id); the last observation to set a field wins
      - provenance: field -> id of the observation that set it

    Returns the DETERMINISTIC core only. Neotoma's response also carries computed_at (a wall-clock
    response timestamp); that is metadata, not data-path, so it is deliberately excluded from the
    anchored root. Everything here is a pure function of (observations, at, at_ingested).
    """
    bounded = [o for o in observations if o["observed_at"] <= at and o["created_at"] <= at_ingested]
    bounded.sort(key=lambda o: (o["observed_at"], o["id"]))
    fields, provenance = {}, {}
    for o in bounded:
        for k, v in o.get("values", {}).items():
            fields[k] = v
            provenance[k] = o["id"]
    head = bounded[0] if bounded else {}
    return {
        "entity_id": head.get("entity_id"),
        "entity_type": head.get("entity_type"),
        "schema_version": head.get("schema_version"),
        "at": at,
        "at_ingested": at_ingested,
        "snapshot": fields,
        "provenance": provenance,
        "observation_count": len(bounded),
    }


def snapshot_root(core):
    """The canonical root Markovian anchors: SHA-256 over the RFC 8785 canonical snapshot core."""
    return "0x" + hashlib.sha256(jcs(core)).hexdigest()
