# End-to-end repro: `useChat` + FastAPI + `VercelAIAdapter`

Reproduces the bug as a user actually encounters it: a real React frontend using `@ai-sdk/react`'s `useChat` hook POSTs to a FastAPI backend that wires `VercelAIAdapter` directly to a `pydantic_ai.Agent`. The frontend's message history includes a `dynamic-tool` part with `providerExecuted`, and the server returns **HTTP 422** with a Pydantic `extra_forbidden` validation error.

## Layout

- `server/` — FastAPI + `pydantic_ai.Agent` + OpenAI. Single `/api/chat` endpoint, no sanitizer middleware.
- `web/` — Vite + React 19 + `@ai-sdk/react@3.0.134` + `ai@6.0.57` (matching the tag `pydantic_ai`'s `request_types.py` mirrors).

## Run

```bash
# Terminal 1 — backend
cd e2e/server
cp .env.example .env  # then set OPENAI_API_KEY
export $(cat .env | xargs)
uv run uvicorn main:app --reload --port 8000

# Terminal 2 — frontend
cd e2e/web
pnpm install
pnpm dev
```

Open http://localhost:5173 and click **Reproduce bug**. The browser's network panel will show a 422 from `/api/chat`; the page renders the `extra_forbidden` error returned by Pydantic.

## How the trigger works

`useChat` is initialized with a pre-seeded `messages` array containing a prior assistant turn whose `parts` include:

```ts
{
  type: "dynamic-tool",
  toolName: "search_files",
  toolCallId: "seed-call-1",
  state: "output-available",
  input: { name_query: "test" },
  output: { results: [{ name: "test.txt" }] },
  providerExecuted: false,   // <-- the field that triggers the bug
}
```

When the user submits a follow-up, `useChat` POSTs the *full* message history (including that pre-seeded part) to `/api/chat`. The backend's `VercelAIAdapter.build_run_input()` calls Pydantic to validate the body against the `RequestData` discriminated union. The `DynamicTool*Part` classes don't declare `provider_executed` and inherit `extra='forbid'`, so validation fails with seven `extra_forbidden` errors (one per dynamic-tool state variant).

## Reference: confirmed via curl

```
$ curl -sw "HTTP %{http_code}\n" -X POST http://localhost:8000/api/chat \
       -H "Content-Type: application/json" --data @repro-body.json -o response.json
HTTP 422

$ jq '[.detail[] | select(.loc | map(tostring) | contains(["DynamicTool"]) and contains(["providerExecuted"]))]' response.json | head -20
[
  { "loc": ["body","submit-message","messages","1","parts","0","DynamicToolInputStreamingPart","providerExecuted"], "msg": "Extra inputs are not permitted", "type": "extra_forbidden" },
  ...
]
```
