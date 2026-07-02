#!/usr/bin/env python3
"""
Example: a LangChain callback that turns an agent run into an anchorable audit trail.

Every LLM call, tool call, and chain step is appended as a record. When the run
ends, call .anchor() to hash-chain the records and commit the head, so the whole
session becomes tamper-evident and independently verifiable.

This is an example, not part of the core tool. It needs LangChain:

    pip install langchain-core

Callback method signatures vary across LangChain versions, so treat this as a
starting point and adapt the handlers you care about. The core stays
dependency-free; only this example imports langchain.

    from examples.langchain_callback import AuditAnchorCallback
    cb = AuditAnchorCallback()
    agent.invoke(inputs, config={"callbacks": [cb]})
    manifest = cb.anchor(label="support-agent run 8842")
    # manifest["anchor"]["verify_url"] is publicly checkable
"""
import os
import sys
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import audit_anchor

from langchain_core.callbacks import BaseCallbackHandler


class AuditAnchorCallback(BaseCallbackHandler):
    """Collect agent-run events as records, then anchor them."""

    def __init__(self):
        self.records = []

    def _log(self, event, **data):
        rec = {
            "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "event": event,
            **data,
        }
        # store each record as canonical bytes, hashed exactly as written
        self.records.append(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode())

    def on_llm_start(self, serialized, prompts, **kwargs):
        self._log("llm_start", model=(serialized or {}).get("name"), n_prompts=len(prompts))

    def on_llm_end(self, response, **kwargs):
        self._log("llm_end")

    def on_tool_start(self, serialized, input_str, **kwargs):
        self._log("tool_start", tool=(serialized or {}).get("name"))

    def on_tool_end(self, output, **kwargs):
        self._log("tool_end")

    def on_chain_end(self, outputs, **kwargs):
        self._log("chain_end")

    def anchor(self, label="langchain agent run"):
        """Hash-chain the collected records and anchor the head."""
        chain = audit_anchor.build_chain(self.records)
        head = audit_anchor.chain_head(chain)
        anchor = audit_anchor.anchor_head(head, label)
        return {"entries": len(chain), "chain_head": head, "anchor": anchor, "chain": chain}

    def verify(self, chain):
        """Recompute from the collected records and check integrity."""
        return audit_anchor.verify_chain(self.records, chain)
