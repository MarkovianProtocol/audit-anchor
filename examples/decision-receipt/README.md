# decision-receipt worked vector (independent reference anchor)

An independent reference fixture for `proofbundle/predicates/decision-receipt/v0.1`, so the
predicate can ship with a second-implementation cross-check from day one.

Rule (as pinned in b7n0de/proofbundle#7):
  anchor root = SHA-256 over the RFC 8785 (JCS) canonical statement bytes (the content root).
  Signatures are a separate layer over the same content. `evidenceRefs` bind to the evidence
  content root, so the reference survives re-signing, counter-signing, and key rotation.

Files:
  evidence_eval_result.json   an eval-result statement (the evidence)
  decision_receipt.json       a decision-receipt/v0.1 statement; evidenceRefs[0].digest = evidence content root
  *.jcs                       the RFC 8785 canonical bytes that get hashed
  decision_receipt.jcs.ots    OpenTimestamps proof over the decision content root
  MANIFEST.json               the two content roots + the rule
  verify.py                   recompute roots, check the evidenceRef binding, verify the anchor

Content roots:
  evidence : a86058b3...  (see MANIFEST.json for full)
  decision : 16b80b4c...  <- this is what is anchored to Bitcoin

Run:
  pip install rfc8785        # plus the OpenTimestamps client `ots`
  python3 verify.py

Scope: existence and ordering only. The anchor fixes that the decision existed no later than its
Bitcoin block, independent of any issuer's clock, and that it referenced this exact evidence content.
It says nothing about whether the decision was correct.

Note: the anchor is pending until its calendar commitment lands in a Bitcoin block; run
`ots upgrade decision_receipt.jcs.ots` after a few blocks to pin the height. The predicateType
string is inside the anchored bytes; align it to the final vendored URI and re-anchor if it changes.
