# Agents and the Model Context Protocol
"""
An AGENT is a loop: the model looks at the conversation, either answers or asks to CALL A TOOL,
your code runs the tool, appends the result (the "observation"), and the model goes again.

    while not done:
        turn = model(messages)             # plan: text and/or tool calls
        if no tool calls: return turn.text # stopping condition: final answer
        run each tool, append results      # act + observe

The model never executes anything; YOUR code does. That is where safety lives. Guardrails:
- STOP CONDITIONS: final answer, `max_steps`, repeated identical calls (loop detection), and
  budgets (tokens, dollars, wall-clock). A loop without a hard cap is a bill waiting to happen.
- ALLOWLIST: the model can only call tools you registered; unknown names are errors.
- ARGUMENT VALIDATION: check the JSON the model produced against the tool's schema.
- APPROVAL: dangerous tools (delete, send email, spend money) need a human/policy yes first.
- ERRORS ARE OBSERVATIONS: a failing tool returns `is_error` text so the model can recover.
- Treat tool OUTPUT as untrusted data (prompt injection): it must not gain the authority of
  your system prompt.

MODEL CONTEXT PROTOCOL (MCP) standardizes how tools are exposed. An MCP SERVER publishes tools
(plus resources and prompts) with JSON schemas; an MCP CLIENT lists and calls them over stdio or
HTTP. Write a tool once, use it from Claude Desktop, IDEs, or your own agent. The official
`mcp` package (v2) provides `MCPServer` (named `FastMCP` in v1: `from mcp.server.fastmcp
import FastMCP`) and `Client`. In tests the client can connect to the server IN-PROCESS, which
is what we do below. To serve for real: `server.run()` (stdio) or `server.run("streamable-http")`.

Here the model is a SCRIPTED fake so everything runs offline. With ANTHROPIC_API_KEY set the
same loop drives Claude through `claude_model` (manual tool-use loop, model `claude-opus-5-5`).
Run: uv run python -m t06_applied_ml_llm.m_15_agents_and_mcp
"""

import ast
import asyncio
import inspect
import json
import operator
import os
from collections.abc import Callable
from dataclasses import dataclass, field

CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
PY_TO_JSON = {int: "integer", float: "number", str: "string", bool: "boolean"}


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ModelTurn:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict
    fn: Callable[..., object]
    dangerous: bool = False


@dataclass
class AgentResult:
    answer: str | None
    stop_reason: str  # "final" | "max_steps" | "loop"
    steps: int
    trace: list[tuple[str, dict, str]]


ModelFn = Callable[[list[dict]], ModelTurn]


# Example: derive a tool schema from a typed function
def tool(fn: Callable[..., object], dangerous: bool = False) -> ToolSpec:
    params = inspect.signature(fn).parameters
    props = {n: {"type": PY_TO_JSON[p.annotation]} for n, p in params.items()}
    required = [n for n, p in params.items() if p.default is inspect.Parameter.empty]
    schema = {
        "type": "object",
        "properties": props,
        "required": required,
        "additionalProperties": False,
    }
    return ToolSpec(fn.__name__, (inspect.getdoc(fn) or "").split("\n")[0], schema, fn, dangerous)


def validate_args(schema: dict, args: dict) -> str | None:
    types = {"integer": int, "number": (int, float), "string": str, "boolean": bool}
    for name in schema["required"]:
        if name not in args:
            return f"missing argument '{name}'"
    for name, value in args.items():
        if name not in schema["properties"]:
            return f"unexpected argument '{name}'"
        if not isinstance(value, types[schema["properties"][name]["type"]]):
            return f"argument '{name}' must be {schema['properties'][name]['type']}"
    return None


# Example: the agent loop with guardrails
def execute(
    call: ToolCall, tools: dict[str, ToolSpec], approve: Callable[[ToolCall], bool] | None
) -> tuple[str, bool]:
    spec = tools.get(call.name)
    if spec is None:
        return f"error: unknown tool '{call.name}'", True
    if (problem := validate_args(spec.input_schema, call.args)) is not None:
        return f"error: {problem}", True
    if spec.dangerous and not (approve and approve(call)):
        return "blocked: this tool needs human approval", True
    try:
        return str(spec.fn(**call.args)), False
    except Exception as exc:  # tool bugs become observations, not crashes
        return f"error: {exc}", True


def run_agent(
    task: str,
    model: ModelFn,
    tools: dict[str, ToolSpec],
    *,
    max_steps: int = 6,
    approve: Callable[[ToolCall], bool] | None = None,
) -> AgentResult:
    messages: list[dict] = [{"role": "user", "content": task}]
    trace: list[tuple[str, dict, str]] = []
    recent: list[str] = []
    for step in range(1, max_steps + 1):
        turn = model(messages)
        if not turn.tool_calls:
            return AgentResult(turn.text, "final", step, trace)
        messages.append({"role": "assistant", "text": turn.text, "tool_calls": turn.tool_calls})
        results = []
        for call in turn.tool_calls:
            recent.append(f"{call.name}:{json.dumps(call.args, sort_keys=True)}")
            if len(recent) >= 3 and len(set(recent[-3:])) == 1:
                return AgentResult(None, "loop", step, trace)  # same call 3x in a row
            output, is_error = execute(call, tools, approve)
            trace.append((call.name, call.args, output))
            results.append(
                {"id": call.id, "name": call.name, "content": output, "is_error": is_error}
            )
        messages.append({"role": "tool", "results": results})
    return AgentResult(None, "max_steps", max_steps, trace)


# Example: a scripted fake model (deterministic), and a real Claude adapter
def scripted(turns: list[ModelTurn]) -> ModelFn:
    queue = list(turns)

    def model(_messages: list[dict]) -> ModelTurn:
        return queue.pop(0) if queue else ModelTurn(text="(script exhausted)")

    return model


def claude_model(tools: dict[str, ToolSpec]) -> ModelFn:
    import anthropic

    client = anthropic.Anthropic()
    defs = [
        {"name": t.name, "description": t.description, "input_schema": t.input_schema}
        for t in tools.values()
    ]

    def to_api(messages: list[dict]) -> list[dict]:
        api: list[dict] = []
        for m in messages:
            if m["role"] == "user":
                api.append({"role": "user", "content": m["content"]})
            elif m["role"] == "assistant":
                blocks = [{"type": "text", "text": m["text"]}] if m["text"] else []
                blocks += [
                    {"type": "tool_use", "id": c.id, "name": c.name, "input": c.args}
                    for c in m["tool_calls"]
                ]
                api.append({"role": "assistant", "content": blocks})
            else:  # ALL tool results go back together in ONE user message
                blocks = [
                    {
                        "type": "tool_result",
                        "tool_use_id": r["id"],
                        "content": r["content"],
                        "is_error": r["is_error"],
                    }
                    for r in m["results"]
                ]
                api.append({"role": "user", "content": blocks})
        return api

    def model(messages: list[dict]) -> ModelTurn:
        resp = client.messages.create(
            model=CLAUDE_MODEL, max_tokens=2048, tools=defs, messages=to_api(messages)
        )
        if resp.stop_reason == "refusal":
            return ModelTurn(text="(model refused)")
        text = "".join(b.text for b in resp.content if b.type == "text")
        calls = [
            ToolCall(b.id, b.name, dict(b.input)) for b in resp.content if b.type == "tool_use"
        ]
        return ModelTurn(text, calls)

    return model


# Example: some tools
NOTES = {"n1": "Cats sleep a lot.", "n2": "Dogs bark.", "n3": "My cat is named Miso."}
OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}


def calculator(expression: str) -> float:
    """Evaluate an arithmetic expression like '17*3'."""

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in OPS:
            return OPS[type(node.op)](ev(node.left), ev(node.right))
        raise ValueError("unsupported expression")  # never eval() model-written text!

    return ev(ast.parse(expression, mode="eval").body)


def search_notes(query: str) -> str:
    """Return the notes containing the query word."""
    return "\n".join(t for t in NOTES.values() if query.lower() in t.lower()) or "no matches"


def delete_note(note_id: str) -> str:
    """Delete a note permanently."""
    NOTES.pop(note_id, None)
    return f"deleted {note_id}"


# Example: a tiny MCP server, called in-process
def build_mcp_server():
    try:
        from mcp.server.mcpserver import MCPServer  # mcp v2
    except ImportError:  # mcp v1 used a different name and module path
        from mcp.server.fastmcp import FastMCP as MCPServer

    server = MCPServer("notes-demo")

    @server.tool()
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    @server.tool()
    def count_notes(query: str) -> int:
        """Count notes that mention a word."""
        return sum(query.lower() in t.lower() for t in NOTES.values())

    return server


async def call_mcp(server, name: str, args: dict) -> str:
    from mcp import Client  # v2 in-process client: Client(server) needs no subprocess or network

    async with Client(server) as client:
        result = await client.call_tool(name, args)
        return "".join(c.text for c in result.content if c.type == "text")


def mcp_tools_for_agent(server) -> dict[str, ToolSpec]:
    """Bridge: advertise MCP tools to the agent loop and route calls back through MCP."""
    from mcp import Client

    async def list_all():
        async with Client(server) as client:
            return (await client.list_tools()).tools

    specs = {}
    for t in asyncio.run(list_all()):
        specs[t.name] = ToolSpec(
            t.name,
            t.description or "",
            t.input_schema,
            lambda _n=t.name, **kw: asyncio.run(call_mcp(server, _n, kw)),
        )
    return specs


"""
Common mistakes
- No step limit or loop detection: a confused model repeats the same failing call forever.
- Running model-written code or shell commands without a sandbox (and never `eval()` it).
- Returning a Python traceback or secrets in tool output: observations go back to the model
  (and maybe the user). Return short, safe error strings.
- Splitting parallel tool results across several user messages (send them back together).
- Too many tools or vague descriptions: the model picks the wrong one. Few, well-named tools.
- Letting an MCP server expose more than the agent needs (least privilege; separate read/write).

Production notes
- Log every step (messages, tool calls, latency, tokens): traces are how you debug agents.
- Put irreversible actions behind approval, idempotency keys, and dry-run modes.
- For a hosted agent loop with a sandbox, Anthropic's Managed Agents runs the loop for you; the
  Messages API manual loop (this lesson) is the right choice when you host the loop yourself.
- Models can decline (stop_reason "refusal"): handle it as a stop condition.
- Remote MCP servers need auth (OAuth) and input validation; treat them like any public API.
"""

if __name__ == "__main__":
    tools = {
        t.name: t for t in (tool(calculator), tool(search_notes), tool(delete_note, dangerous=True))
    }
    print("schema for calculator:", json.dumps(tools["calculator"].input_schema))

    task = "What is 17*3, and how many notes mention cats?"
    if os.getenv("ANTHROPIC_API_KEY"):
        print("model: Claude", CLAUDE_MODEL)
        result = run_agent(task, claude_model(tools), tools, max_steps=6)
    else:
        print("model: scripted fake (no ANTHROPIC_API_KEY set)")
        script = [
            ModelTurn(
                "I'll compute and search.",
                [
                    ToolCall("t1", "calculator", {"expression": "17*3"}),
                    ToolCall("t2", "search_notes", {"query": "cat"}),
                ],
            ),
            ModelTurn("17*3 is 51 and two notes mention cats."),
        ]
        result = run_agent(task, scripted(script), tools, max_steps=6)
    print(f"-> {result.stop_reason} in {result.steps} steps: {result.answer}")
    for name, args, out in result.trace:
        print(f"   tool {name}({args}) -> {out!r}")

    stuck = scripted(
        [ModelTurn("", [ToolCall(f"x{i}", "search_notes", {"query": "fish"})]) for i in range(10)]
    )
    print("runaway model     ->", run_agent(task, stuck, tools).stop_reason)
    endless = scripted(
        [
            ModelTurn("", [ToolCall(f"y{i}", "calculator", {"expression": f"{i}+1"})])
            for i in range(10)
        ]
    )
    print("endless explorer  ->", run_agent(task, endless, tools, max_steps=3).stop_reason)
    danger = scripted(
        [
            ModelTurn("", [ToolCall("d1", "delete_note", {"note_id": "n1"})]),
            ModelTurn("Could not delete."),
        ]
    )
    res = run_agent("delete n1", danger, tools)
    print("dangerous tool    ->", res.trace[0][2], "| notes intact:", "n1" in NOTES)
    bad = scripted(
        [ModelTurn("", [ToolCall("b1", "calculator", {"expression": 5})]), ModelTurn("done")]
    )
    print("bad arguments     ->", run_agent("x", bad, tools).trace[0][2])

    try:
        server = build_mcp_server()
        mcp_tools = mcp_tools_for_agent(server)
        print("MCP tools:", list(mcp_tools))
        mcp_script = scripted(
            [
                ModelTurn(
                    "",
                    [
                        ToolCall("m1", "add", {"a": 2, "b": 40}),
                        ToolCall("m2", "count_notes", {"query": "cat"}),
                    ],
                ),
                ModelTurn("Done."),
            ]
        )
        res = run_agent("use MCP", mcp_script, mcp_tools)
        print("MCP agent trace:", [(n, o) for n, _, o in res.trace])
    except ImportError as exc:
        print("mcp package unavailable or older than v2; skipping in-process demo:", exc)
