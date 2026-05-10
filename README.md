# pydantic-ai-vercel-dynamic-tool-repro

Minimal repro: `pydantic_ai`'s Vercel AI adapter rejects spec-compliant `providerExecuted` on `dynamic-tool` message parts.

This repo contains two repros:

1. **[`repro.py`](repro.py)** — pure-Python schema proof. Synthesizes a Vercel UI Message payload and hands it to `VercelAIAdapter.build_run_input()` directly. Fast, no React, no API key.
2. **[`e2e/`](e2e/)** — end-to-end via `useChat` from a real React frontend POSTing to a FastAPI + `pydantic_ai.Agent` backend with OpenAI. Demonstrates the bug as users actually hit it.

## Pure-Python repro

```bash
uv run repro.py
```

## Expected output

```
--- dynamic-tool WITH providerExecuted (spec-compliant; should parse) ---
FAIL: 106 total validation errors
      7 of them are 'providerExecuted' on dynamic-tool variants:
        - submit-message.messages.0.parts.0.DynamicToolInputStreamingPart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolInputAvailablePart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolOutputAvailablePart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolOutputErrorPart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolApprovalRequestedPart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolApprovalRespondedPart.providerExecuted: Extra inputs are not permitted
        - submit-message.messages.0.parts.0.DynamicToolOutputDeniedPart.providerExecuted: Extra inputs are not permitted

--- dynamic-tool WITHOUT providerExecuted (workaround; parses) ---
OK: parsed successfully

--- tool-<name> WITH providerExecuted (parses; field IS declared here) ---
OK: parsed successfully
```

## Root cause

`pydantic_ai/ui/vercel_ai/request_types.py` opens with:

> "Vercel AI request types (UI messages). Converted to Python from: https://github.com/vercel/ai/blob/ai%406.0.57/packages/ai/src/ui/ui-messages.ts"

At that exact tag, the upstream TypeScript declares `providerExecuted?: boolean` on the parent `DynamicToolUIPart` (which is then intersected with each state variant):

```ts
export type DynamicToolUIPart = {
  type: 'dynamic-tool';
  toolName: string;
  toolCallId: string;
  title?: string;
  providerExecuted?: boolean;   // <-- declared upstream
} & ( /* state variants */ )
```

The Python conversion correctly carried `provider_executed` onto every `Tool*Part` (the `tool-${NAME}` variants) but **dropped it from all seven `DynamicTool*Part` classes**. It also dropped `title?: string` from the same classes. Combined with `CamelBaseModel(extra='forbid')`, spec-compliant frontend payloads from the Vercel AI SDK fail validation with `extra_forbidden`.

The third case in the repro (`tool-<name> WITH providerExecuted`) shows the asymmetry directly: the same wire field is accepted on the static-tool variants because the static-tool classes did include it.

## Proposed fix

Add the missing optional fields to each of the seven `DynamicTool*Part` classes in `pydantic_ai_slim/pydantic_ai/ui/vercel_ai/request_types.py`:

```python
provider_executed: bool | None = None
title: str | None = None
```

## Versions

Reproduced against `pydantic-ai-slim>=1.90.0`. The current `main` branch still omits these fields on the dynamic-tool variants, so the bug is present on latest as well.
