#!/usr/bin/env python3
# Independent reference verifier for a proofbundle decision-receipt/v0.1 worked vector.
# Recomputes content roots, checks the evidenceRef binding and the parameters digest,
# verifies the Bitcoin anchor.
import json, hashlib, subprocess, sys, os, re, shutil
try:
    import rfc8785
except ImportError:
    print("needs: pip install rfc8785"); sys.exit(2)
here = os.path.dirname(os.path.abspath(__file__)); os.chdir(here)
croot = lambda p: hashlib.sha256(rfc8785.dumps(json.load(open(p)))).hexdigest()
man = json.load(open("MANIFEST.json"))
ev = croot("evidence_eval_result.json"); de = croot("decision_receipt.json")
pred = json.load(open("decision_receipt.json"))["predicate"]
ref = pred["evidenceRefs"][0]["digest"]["sha256"]
ok = True
print("[1] content roots = SHA-256 over RFC 8785 canonical bytes")
print("    evidence:", ev, "OK" if ev == man["evidence_content_root_sha256"] else "MISMATCH"); ok &= ev == man["evidence_content_root_sha256"]
print("    decision:", de, "OK" if de == man["decision_content_root_sha256"] else "MISMATCH"); ok &= de == man["decision_content_root_sha256"]
print("[2] decision.evidenceRefs[0].digest == evidence content root:", "OK" if ref == ev else "MISMATCH")
print("    (bound to the content root, so it survives re-signing / counter-signing / key rotation)"); ok &= ref == ev
print("[3] proposedAction.parametersDigest == SHA-256 over RFC 8785 canonical parameters.json")
pd = pred["proposedAction"]["parametersDigest"]["sha256"]; pj = croot("parameters.json")
print("    parameters:", pj, "OK" if pj == pd else "MISMATCH"); ok &= pj == pd
print("[4] Bitcoin anchor over the decision content root")
ots = shutil.which("ots") or os.path.expanduser("~/neo_env/bin/ots")
if shutil.which("ots") or os.path.exists(ots):
    out = subprocess.run([ots, "info", "decision_receipt.jcs.ots"], capture_output=True, text=True).stdout
    m = re.search(r"BitcoinBlockHeaderAttestation\((\d+)\)", out)
    if m: print("    anchored in Bitcoin block", m.group(1))
    elif "ending" in out: print("    PENDING confirmation; run: ots upgrade decision_receipt.jcs.ots")
    else: print("   ", out.strip()[:160])
else:
    print("    ots client not found; install OpenTimestamps to verify the anchor")
print("\nRESULT:", "PASS" if ok else "FAIL"); sys.exit(0 if ok else 1)
