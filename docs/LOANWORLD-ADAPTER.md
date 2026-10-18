# LoanWorld system-mode adapter (`gradia.loanworld.stdio.v0`)

Any agent stack can run a LoanWorld episode as a subprocess that reads and writes one JSON object per line. The harness owns the world. The agent only sees what the harness sends it.

## Messages

| Direction | Message |
|---|---|
| harness → agent | `{"type": "start", "protocol": "gradia.loanworld.stdio.v0", "scenario_id", "max_acts", "tools": [...], "projection": {...}}` |
| agent → harness | `{"type": "call", "tool": "<name>", "args": {...}}` |
| harness → agent | `{"type": "result", "act": n, "response": {"ok": true, "result": ...} \| {"ok": false, "error": "<code>"}, "events"?: [...]}` |
| harness → agent | `{"type": "end", "outcome": "terminal" \| "censored"}` |

`events` appears when scheduled world events fired after that act: notices, uploads, clock changes. The episode ends when the agent calls `submit` successfully.

## Tools

Run `gradia-universe loanworld-tools` for the machine-readable manifest. Summary:

| Tool | Notes |
|---|---|
| `get_projection`, `list_uploads`, `get_page`, `read_inbox`, `get_conditions` | Reads. `get_page` returns a text layer only for native PDFs, and it may disagree with the pixels. |
| `request_document`, `send_message` | External effects with idempotency keys. `send_message` records whether the channel is one on file for that party. |
| `order_service` | `credit`, `aus`, `appraisal`, `title`, `flood`, `verbal_voe` |
| `clear_condition`, `add_condition`, `flag` | Need at least one citation. |
| `write_los_field` | Needs one citation. Read-only fields refuse. |
| `escalate` | The honest-uncertainty path |
| `submit` | `PRECHECK_PASS`, `CONDITIONAL`, `ESCALATE` or `DECLINE_RECOMMENDED`; open condition IDs; an account of `{claim, citations}` |

A citation is exactly one of:
- `{"upload_id", "page", "bbox_cpt"?, "quote"?}`, with boxes in integer centipoints from the top-left of the page;
- `{"service", "path"?}`, for a service that has returned;
- `{"event_id"}`, for an event the agent has seen.

## Outcomes

`run_stdio_episode` returns `{"outcome", "censor_reason", "acts", "proof_pack"}`.

**Censor reasons:**
- `step_timeout`
- `total_timeout`
- `agent_exited`
- `agent_not_accepting_input`
- `malformed_agent_message`
- `act_budget_exhausted`

Censored episodes are reported apart from model outcomes.

**Proof packs** carry:
- every receipt;
- every occurrence;
- the final world root and per-ledger roots;
- the terminal submission;
- a pack digest.

`gradia_universes.loanworld.tools.verify_proof_pack` checks a pack offline.

## Running your own stack

```bash
python -c "from gradia_universes.loanworld.adapter import run_stdio_episode; ..."
```

Point `command` at your agent, for example `["node", "my-agent.js"]`. The harness never sends case truth, trap labels or sender authenticity, so an agent can't learn them from the protocol.
