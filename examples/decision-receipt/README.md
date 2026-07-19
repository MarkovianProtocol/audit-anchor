# decision-receipt worked vector (independent reference anchor)

Independent cross-implementation fixture for proofbundle decision-receipt/v0.1. This is a conformance fixture: the acme-intent-classifier deploy scenario is illustrative, not a record of a production decision. Passes proofbundle 3.6.1's enforced v0.1 validator in normal and strict mode; canonical bytes and content roots are byte-identical with proofbundle's own RFC 8785 output.

The v0.1 field mapping follows b7n0de's mapping of this repo's earlier fixture in [proofbundle#7](https://github.com/b7n0de/proofbundle/issues/7#issuecomment-5016604636). Relative to that mapping, this repo set the values it owns and nothing else:

- `decisionId` — fresh urn:uuid.
- `proposedAction.parametersDigest` — SHA-256 over the RFC 8785 canonical bytes of `parameters.json` in this directory, so the digest is reproducible by anyone.

`policyEngine: audit-anchor`, `policyId: release-gate/prod`, `decisionPath: release.gate.prod.allow` are the documented fixture policy names for this repo's release-gate example; the repo has no separate formal policy registry. All other values are byte-identical to the mapping above.

Rule (pinned in b7n0de/proofbundle#7): anchor root = SHA-256 over the RFC 8785 (JCS) canonical statement bytes (the content root). Signatures are a separate layer over the same content. evidenceRefs bind to the evidence content root, so the reference survives re-signing, counter-signing, and key rotation.

- decision predicateType: https://b7n0de.com/proofbundle/predicates/decision-receipt/v0.1
- evidence predicateType: https://b7n0de.com/attestation/eval-result/v0.1
- evidence content root: 323adb188f840e90331c920b32a73f348acc5caea8d40f9a84ea384d46c258d4
- decision content root: 97e1d74b810a9fea454ac890c0e17f8a401fb4abbf42827a39aea30846de2fb5 (OpenTimestamps-anchored; the pending .ots upgrades to a Bitcoin block attestation once the calendar commits, via `ots upgrade`)

Run: `pip install rfc8785` plus the OpenTimestamps client `ots`, then `python3 verify.py`.

Scope: existence and ordering only. The anchor fixes that the decision existed no later than its Bitcoin block, independent of any issuer's clock, and that it referenced this exact evidence content. It says nothing about whether the decision was correct.
