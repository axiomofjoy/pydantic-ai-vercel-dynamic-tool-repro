"""FastAPI server wiring `VercelAIAdapter` directly to a `pydantic_ai.Agent`.

Deliberately unsanitized — no preprocessing of incoming bodies — so the
``providerExecuted`` field on a ``dynamic-tool`` part from the Vercel AI SDK
frontend triggers a Pydantic ``extra_forbidden`` validation error and a 422.

Run:
    OPENAI_API_KEY=... uv run uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.ui.vercel_ai import VercelAIAdapter
from pydantic_ai.ui.vercel_ai.request_types import RequestData
from pydantic_ai.ui.vercel_ai.response_types import BaseChunk
from starlette.requests import Request
from starlette.responses import Response

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_agent() -> Agent[None, str]:
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required to start the server.")
    agent: Agent[None, str] = Agent(
        OpenAIChatModel("gpt-4o-mini"),
        system_prompt="You are a helpful assistant. Keep replies short.",
    )

    @agent.tool_plain
    def search_files(name_query: str) -> dict[str, Any]:
        """A toy tool the frontend pre-seeds a call to."""
        return {"results": [{"name": f"{name_query}.txt"}]}

    return agent


_agent = _build_agent()


@app.post("/api/chat")
async def chat(body: RequestData, request: Request) -> Response:
    adapter: VercelAIAdapter[None, str] = VercelAIAdapter(
        agent=_agent,
        run_input=body,
        accept=request.headers.get("accept"),
    )

    async def _stream() -> AsyncIterator[BaseChunk]:
        async for chunk in adapter.run_stream():
            yield chunk

    return adapter.streaming_response(_stream())
