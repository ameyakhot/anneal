# Anneal

Optimal context selection for AI coding assistants. Cooling random context down to exactly what your AI needs.

Anneal reads your codebase's structural graph (from Graphify or code-review-graph),
formulates "which chunks are optimal?" as a QUBO problem, solves with simulated
annealing, and returns the minimum context set for your task.

## How It Works

1. Reads codebase graph (Graphify `graph.json` or code-review-graph SQLite)
2. Generates candidate chunks (keyword matching + graph topology)
3. Formulates QUBO: minimize token cost, maximize relevance, reward dependency coverage
4. Solves via simulated annealing (SpinChain engine)
5. Returns stability-ranked, dependency-ordered chunks within your token budget

## Requirements

- Python 3.11+
- At least one graph tool: [Graphify](https://github.com/safishamsi/graphify) or [code-review-graph](https://github.com/nicholasgasior/code-review-graph)

## Installation

```bash
pip install anneal-context
```

Or with uv:
```bash
uv tool install anneal-context
```

## Setup

**1. Install a graph tool** (required):

```bash
# code-review-graph
npx code-review-graph install

# Graphify (Claude Code)
/plugin marketplace add safishamsi/graphify && /graphify
```

**2. Create `.anneal/config.toml`** in your project root:

```toml
[budget]
default_tokens = 5000
strategy = "balanced"   # "minimal" | "balanced" | "thorough"

[solver]
backend = "simulated-annealing"
num_reads = 100
num_sweeps = 1000
```

Add `.anneal/` to your `.gitignore`.

## MCP Server Setup

### Claude Code

Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "anneal": {
      "command": "anneal-server"
    }
  }
}
```

### Gemini CLI

Add to `~/.gemini/settings.json`:
```json
{
  "mcpServers": {
    "anneal": {
      "command": "anneal-server"
    }
  }
}
```

### OpenAI Codex CLI

Add to `~/.codex/config.toml`:
```toml
[[mcp_servers]]
name = "anneal"
command = "anneal-server"
```

### Cursor / VS Code + Copilot / Aider

Any MCP-compatible client: run `anneal-server` via stdio transport.

## Tools

### `get_optimal_context`

```
Parameters:
  task_description: str     -- what you want to do
  token_budget: int | None  -- max tokens (default: 5000)
  include_files: list[str]  -- always include these paths
  exclude_files: list[str]  -- never include these paths
  strategy: str             -- "balanced" | "minimal" | "thorough"

Returns:
  selected_chunks: list[{path, content, relevance_score, tokens}]
  total_tokens: int
  budget_utilization: float
  stability_score: float
  dependency_graph: dict
```

### `get_status`

Returns graph source availability, node counts, solver config.

## Development

```bash
git clone https://github.com/ameyakhot/anneal
cd anneal
uv venv && source .venv/bin/activate
uv pip install -e /path/to/spinchain
uv pip install -e ".[dev]"
python -m pytest tests/ -v
```

## License

MIT
