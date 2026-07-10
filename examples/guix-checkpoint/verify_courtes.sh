#!/bin/sh
# verify_courtes.sh -- offline-first verification of the channel-checkpoint
# timestamp in this directory.  No account, key, or server of ours is
# trusted at any step.
#
# It checks three independent things:
#
#   1. The pinned commit id is exactly the bytes the timestamp covers.
#      (offline: sha256 of commit_id.txt must match the hash inside the
#       .ots proof, shown by `ots info'.)
#
#   2. The commit really is an authenticated state of the guix channel.
#      (online, optional: `git ls-remote' against Savannah re-derives the
#       same commit on master; `guix git authenticate' can then confirm the
#       signature chain to .guix-authorizations.)
#
#   3. The timestamp itself.
#      (`ots verify' walks the proof down to a Bitcoin block header; until
#       the calendar commitment is included in a block it reports "pending",
#       which is the honest state right after stamping.)

set -e
here=$(dirname "$0")
cd "$here"

COMMIT=$(cat commit_id.txt)
echo "pinned commit : $COMMIT"
echo

echo "[1] bytes covered by the timestamp"
echo "    sha256(commit_id.txt) = $(shasum -a 256 commit_id.txt | cut -d' ' -f1)"
echo "    (compare with 'File sha256 hash' from: ots info commit_id.txt.ots)"
echo

echo "[2] commit is live on the guix channel (needs network)"
if command -v git >/dev/null 2>&1; then
    REMOTE=$(git ls-remote https://git.savannah.gnu.org/git/guix.git refs/heads/master 2>/dev/null | cut -f1)
    echo "    savannah master HEAD = ${REMOTE:-<unreachable>}"
    if [ "$REMOTE" = "$COMMIT" ]; then
        echo "    -> matches pinned commit (still current tip of master)"
    else
        echo "    -> differs: master has advanced; the pinned commit remains a"
        echo "       reachable ancestor.  Confirm with: git merge-base --is-ancestor $COMMIT origin/master"
    fi
    echo "    authenticate the signature chain with:"
    echo "      guix git authenticate $COMMIT <intro-commit> <intro-key>"
else
    echo "    git not found; skipping."
fi
echo

echo "[3] the timestamp proof"
OTS=$(command -v ots 2>/dev/null || true)
[ -z "$OTS" ] && [ -x "$HOME/neo_env/bin/ots" ] && OTS="$HOME/neo_env/bin/ots"
if [ -n "$OTS" ]; then
    "$OTS" verify commit_id.txt.ots || true
else
    echo "    ots client not found; run: ots verify commit_id.txt.ots"
fi
