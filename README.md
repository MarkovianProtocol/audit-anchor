# audit-anchor

Anchor any existing audit log so a third party can confirm it has not been altered, without trusting the operator.

`audit_anchor.py` is a standalone, standard-library-only Python tool. It takes an append-only audit log you already keep, hashes each record byte for byte, hash-chains the records, and commits the chain head to the Markovian chain, which is anchored to Bitcoin via OpenTimestamps. It does not capture events, it does not reinterpret your records, it does not judge whether the content is correct, and it is not a compliance system.

## The problem

A growing set of rules requires audit trails that are tamper-evident, time-stamped, and independently verifiable by a third party, without relying on the operator's own systems. An operator-run log store is weakest at exactly that last bar: the operator controls it, so an auditor is trusting the operator not to have rewritten it. audit-anchor closes that gap by committing the log to a ledger the operator cannot rewrite.

## Install

Python 3, standard library only, no dependencies.

```
git clone https://github.com/MarkovianProtocol/audit-anchor
cd audit-anchor
```

That is it. There is nothing to install.

## Usage

Anchor a log:

```
python3 audit_anchor.py anchor yourlog.jsonl --label "my audit trail" --out anchor.json
```

This writes `anchor.json`, a manifest holding the hash chain, the chain head, and the anchor (merkle root and verify URL).

Verify it later:

```
python3 audit_anchor.py verify yourlog.jsonl --anchor anchor.json
```

This recomputes the chain from the raw log and reports PASS or FAIL. Run the built-in offline test, which includes tamper and reorder detection, with:

```
python3 audit_anchor.py --selftest
```

### Example

A three-line log, `examples/sample_audit_log.jsonl`:

```
{"seq":1,"action":"create","record":"BATCH-2287"}
{"seq":2,"action":"modify","record":"BATCH-2287","by":"analyst-42"}
{"seq":3,"action":"output","record":"BATCH-2287","result":"pass"}
```

Anchor it, then edit any line and run `verify`. The check returns FAIL and names the record that changed.

## How verification works (three tiers)

- **Tier 1, local.** Recompute the chain from the raw records. Needs nobody.
- **Tier 2, external anchor.** Confirm the head is recorded on the Markovian chain at the verify URL, an append-only ledger the operator cannot rewrite.
- **Tier 3, Bitcoin.** The Markovian chain is anchored to Bitcoin via OpenTimestamps. Fetch the `.ots` proof and check it with the OpenTimestamps client. Once it carries a Bitcoin attestation, this needs nothing from Markovian either. Tier 3 matures over time and is not instant.

## What it maps to

Each of these requires tamper-evident, time-stamped, independently verifiable audit trails:

- **EU AI Act Article 12** — https://markovianprotocol.com/compliance.html
- **FDA 21 CFR Part 11, section 11.10(e)** — https://markovianprotocol.com/fda-part11.html
- **SEC Rule 17a-4(f) and CFTC Rule 1.31** — https://markovianprotocol.com/sec-17a4.html

## Scope and limits

audit-anchor provides tamper-evidence, timestamping, and operator-independent verifiability of a record. It does not capture events for you, it does not judge whether the logged content is correct, and it is not a compliance system and not legal advice. Automatic capture and retention of the log remain the operator's responsibility.

## License

MIT
