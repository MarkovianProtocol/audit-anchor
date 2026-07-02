#!/usr/bin/env python3
"""
Example: expose audit-anchor as Model Context Protocol (MCP) tools.

Lets any MCP-aware agent anchor its own audit log and verify one, in-session.
This is an example, not part of the core tool. It needs the MCP SDK:

    pip install mcp

Run it as an MCP server:

    python examples/mcp_tool.py

Then point an MCP client (Claude Desktop, an agent runtime, etc.) at it.
The core stays dependency-free; only this integration example uses `mcp`.
"""
import os
import sys

# make the repo-root audit_anchor module importable when run from anywhere
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audit_anchor

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("audit-anchor")


def _read_records(path):
    """Read a newline-delimited log into a list of raw record bytes."""
    with open(path, "rb") as f:
        return [line.rstrip(b"\n") for line in f.readlines() if line.rstrip(b"\n")]


@mcp.tool()
def anchor_audit_log(path: str, label: str = "audit trail") -> dict:
    """Hash-chain a newline-delimited audit log and anchor the chain head.

    Returns a manifest with the chain, the chain head, and the anchor
    (merkle root and verify URL). The head can later be checked against Bitcoin.
    """
    records = _read_records(path)
    chain = audit_anchor.build_chain(records)
    head = audit_anchor.chain_head(chain)
    anchor = audit_anchor.anchor_head(head, label)
    return {"entries": len(chain), "chain_head": head, "anchor": anchor, "chain": chain}


@mcp.tool()
def verify_audit_log(path: str, chain: list) -> dict:
    """Recompute the chain from the raw log and check it against a stored chain.

    Returns whether the log is intact and, if not, where it diverges. Editing
    any record in the log makes this fail and names the record that changed.
    """
    records = _read_records(path)
    ok, reason = audit_anchor.verify_chain(records, chain)
    recomputed_head = audit_anchor.chain_head(audit_anchor.build_chain(records))
    return {"ok": ok, "reason": reason, "recomputed_head": recomputed_head}


if __name__ == "__main__":
    mcp.run()
