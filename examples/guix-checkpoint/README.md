# An unowned timestamp for a Guix channel checkpoint

`guix git authenticate` establishes *who* signed a channel state and *what*
that state is: every commit is authenticated against `.guix-authorizations`,
and the commit id is a Git object name that already fixes the tree.  What it
does not, and cannot, give you is an independent *when* -- a proof that a
given authenticated state existed by some point in time, that rests on no
server, no key, and no operator who could later restamp or backdate it.

This directory supplies that missing "when" for one concrete checkpoint of
the `guix` channel.

## What was pinned

    channel : guix
    url     : https://git.savannah.gnu.org/git/guix.git
    branch  : master
    commit  : 1798fa9f53f9e03697daaafb9d618e929855fa30
    author  : Anderson Torres <anderson.torres.8519@gmail.com>, 2026-07-08
    commit  : Nguyễn Gia Phong <cnx@loang.net>, 2026-07-10
    subject : gnu: Move pegtl to (gnu packages compiler-tools).

This is exactly the tuple `guix describe -f channels' emits (see
`channels.scm').  The commit carries `.guix-authorizations', so it is an
authenticated channel state, not an arbitrary object.

## What was done

The 40-character commit id was written verbatim to `commit_id.txt' (lower-case
hex, no trailing newline) and timestamped with OpenTimestamps.  The proof in
`commit_id.txt.ots' commits to the SHA-256 of that file and, once the
calendar's commitment is confirmed, to a public append-only clock that no
single party owns or can rewind.

Nothing about the channel changes.  The commit id is anchored byte-for-byte;
there is no new format to adopt, no canonicalization step, and nothing for a
Guix user to trust beyond what they already verify with
`guix git authenticate'.

## Files

    commit_id.txt        the pinned commit id (the bytes the proof covers)
    commit_id.txt.ots    the OpenTimestamps proof
    channels.scm         the checkpoint as `guix describe -f channels' output
    verify_courtes.sh    offline-first verification (bytes / channel / time)
    transcript.txt       exact commands and output from building this package

## Verify

    sh verify_courtes.sh

or, step by step:

    ots info   commit_id.txt.ots     # shows the SHA-256 it commits to
    shasum -a 256 commit_id.txt      # must equal that hash
    ots verify commit_id.txt.ots     # walks the proof down to a block header

## Honest status

The timestamp was submitted to the OpenTimestamps calendars and is currently
**pending** confirmation: the aggregated commitment has not yet been included
in a block.  This is the expected state immediately after stamping and
typically clears within an hour or two.  Until then `ots verify' reports
"Pending confirmation"; it is not, and must not be read as, a confirmed
timestamp.  Run `ots upgrade commit_id.txt.ots' once, later, to fold the
inclusion path into the proof, after which verification is fully offline.
