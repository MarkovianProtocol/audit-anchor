;; -*- mode: scheme -*-
;;
;; Channel checkpoint pinned by this package.  This is the exact object
;; `guix describe -f channels' emits: a fully-resolved (name, url, branch,
;; commit) tuple that names one authenticated state of the `guix' channel.
;;
;; The commit id below is a Git object name -- a SHA-1 over the commit and
;; its tree -- so it already fixes the content.  Nothing is re-hashed or
;; canonicalized: the timestamp proof in this directory is bound to this
;; exact 40-character string.

(list (channel
        (name 'guix)
        (url "https://git.savannah.gnu.org/git/guix.git")
        (branch "master")
        (commit "1798fa9f53f9e03697daaafb9d618e929855fa30")))
