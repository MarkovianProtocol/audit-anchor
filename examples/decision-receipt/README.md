# decision-receipt worked vector (independent reference anchor)

Independent cross-implementation fixture for proofbundle decision-receipt/v0.1. Passes proofbundle's enforced v0.1 validator; content roots are byte-identical with proofbundle's own RFC 8785 output.

Rule (pinned in b7n0de/proofbundle#7): anchor root = SHA-256 over the RFC 8785 (JCS) canonical statement bytes (the content root). Signatures are a separate layer over the same content. evidenceRefs bind to the evidence content root, so the reference survives re-signing, counter-signing, and key rotation.

- decision predicateType: https://b7n0de.com/proofbundle/predicates/decision-receipt/v0.1
- evidence predicateType: https://b7n0de.com/attestation/eval-result/v0.1
- evidence content root: 323adb188f840e90331c920b32a73f348acc5caea8d40f9a84ea384d46c258d4
- decision content root: ff05e3e0126e31090511f9e42494bbde4d86c9b1a9a0a9570850c42e8546029b (anchored to Bitcoin)

Run: `pip install rfc8785` plus the OpenTimestamps client `ots`, then `python3 verify.py`.

Scope: existence and ordering only. The anchor fixes that the decision existed no later than its Bitcoin block, independent of any issuer's clock, and that it referenced this exact evidence content. It says nothing about whether the decision was correct.
