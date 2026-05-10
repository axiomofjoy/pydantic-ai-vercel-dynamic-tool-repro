import { useChat } from "@ai-sdk/react";
import { DefaultChatTransport, type UIMessage } from "ai";

const SEEDED_HISTORY: UIMessage[] = [
  {
    id: "seed-user-1",
    role: "user",
    parts: [{ type: "text", text: "Find files named test." }],
  },
  {
    id: "seed-assistant-1",
    role: "assistant",
    parts: [
      {
        type: "dynamic-tool",
        toolName: "search_files",
        toolCallId: "seed-call-1",
        state: "output-available",
        input: { name_query: "test" },
        output: { results: [{ name: "test.txt" }] },
        providerExecuted: false,
      } as unknown as UIMessage["parts"][number],
    ],
  },
];

export function App() {
  const { messages, sendMessage, status, error } = useChat({
    transport: new DefaultChatTransport({ api: "/api/chat" }),
    messages: SEEDED_HISTORY,
  });

  const reproduce = () => {
    sendMessage({ text: "Hi" });
  };

  return (
    <div
      style={{ maxWidth: 720, margin: "40px auto", fontFamily: "system-ui" }}
    >
      <h1>pydantic-ai vercel dynamic-tool repro</h1>
      <p>
        The chat below is pre-seeded with one prior turn containing a{" "}
        <code>dynamic-tool</code> part with <code>providerExecuted: false</code>{" "}
        — a field the Vercel AI SDK declares but <code>pydantic_ai</code>'s
        Python port omits from all <code>DynamicTool*Part</code> classes. Click
        the button to POST a follow-up message; the backend will reject the
        request with a Pydantic <code>extra_forbidden</code> validation error.
      </p>

      <button
        onClick={reproduce}
        disabled={status === "streaming" || status === "submitted"}
        style={{ padding: "10px 16px", fontSize: 16, cursor: "pointer" }}
      >
        Reproduce bug
      </button>

      <p>
        <strong>Status:</strong> {status}
      </p>

      {error && (
        <div
          style={{
            background: "#fee",
            border: "1px solid #c00",
            padding: 12,
            marginTop: 12,
            whiteSpace: "pre-wrap",
          }}
        >
          <strong>Error from /api/chat:</strong>
          {"\n"}
          {error.message}
        </div>
      )}

      <h2>Messages</h2>
      <ol>
        {messages.map((m) => (
          <li key={m.id}>
            <strong>{m.role}</strong>:{" "}
            <code>{JSON.stringify(m.parts, null, 2)}</code>
          </li>
        ))}
      </ol>
    </div>
  );
}
