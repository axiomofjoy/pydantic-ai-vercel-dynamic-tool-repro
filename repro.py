"""Minimal repro: pydantic_ai's Vercel AI adapter rejects spec-compliant
``providerExecuted`` on ``dynamic-tool`` message parts.

The Vercel AI SDK's ``DynamicToolUIPart`` declares ``providerExecuted?: boolean``
at the parent level (see ``packages/ai/src/ui/ui-messages.ts`` at tag ``ai@6.0.57``,
which is the exact tag pydantic_ai's ``request_types.py`` claims to mirror).

pydantic_ai's Python conversion dropped that field from every ``DynamicTool*Part``
variant. Combined with ``CamelBaseModel(extra='forbid')``, a spec-compliant payload
fails validation.

Run:
    uv run repro.py
"""

from __future__ import annotations

import json

from pydantic import ValidationError
from pydantic_ai.ui.vercel_ai import VercelAIAdapter


def _submit_message_with_dynamic_tool_part(*, include_provider_executed: bool) -> bytes:
    part: dict[str, object] = {
        "type": "dynamic-tool",
        "toolName": "search_files",
        "toolCallId": "call-1",
        "state": "output-available",
        "input": {"name_query": "test"},
        "output": {"results": []},
    }
    if include_provider_executed:
        part["providerExecuted"] = False

    body = {
        "trigger": "submit-message",
        "id": "req-1",
        "messages": [
            {
                "id": "msg-1",
                "role": "assistant",
                "parts": [part],
            }
        ],
    }
    return json.dumps(body).encode()


def _submit_message_with_static_tool_part(*, include_provider_executed: bool) -> bytes:
    part: dict[str, object] = {
        "type": "tool-search_files",
        "toolCallId": "call-1",
        "state": "output-available",
        "input": {"name_query": "test"},
        "output": {"results": []},
    }
    if include_provider_executed:
        part["providerExecuted"] = False

    body = {
        "trigger": "submit-message",
        "id": "req-1",
        "messages": [
            {
                "id": "msg-1",
                "role": "assistant",
                "parts": [part],
            }
        ],
    }
    return json.dumps(body).encode()


def _try_parse(label: str, body: bytes) -> None:
    print(f"--- {label} ---")
    try:
        VercelAIAdapter.build_run_input(body)
        print("OK: parsed successfully\n")
    except ValidationError as exc:
        relevant = [
            err
            for err in exc.errors()
            if "DynamicTool" in ".".join(str(p) for p in err["loc"])
            and err["loc"][-1] == "providerExecuted"
        ]
        print(f"FAIL: {exc.error_count()} total validation errors")
        if relevant:
            print(f"      {len(relevant)} of them are 'providerExecuted' on dynamic-tool variants:")
            for err in relevant:
                loc = ".".join(str(p) for p in err["loc"])
                print(f"        - {loc}: {err['msg']}")
        print()


def main() -> None:
    _try_parse(
        "dynamic-tool WITH providerExecuted (spec-compliant; should parse)",
        _submit_message_with_dynamic_tool_part(include_provider_executed=True),
    )
    _try_parse(
        "dynamic-tool WITHOUT providerExecuted (workaround; parses)",
        _submit_message_with_dynamic_tool_part(include_provider_executed=False),
    )
    _try_parse(
        "tool-<name> WITH providerExecuted (parses; field IS declared here)",
        _submit_message_with_static_tool_part(include_provider_executed=True),
    )


if __name__ == "__main__":
    main()
