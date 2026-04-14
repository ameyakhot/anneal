# Anneal

Optimal context selection for AI coding assistants. Cooling random context down to exactly what your AI needs.

Anneal reads your codebase's structural graph, formulates "which chunks are optimal?" as a QUBO problem, solves with simulated annealing, and returns the minimum context set for your task.

## Quick Start

```bash
pip install anneal-context
cd your-project
anneal init          # builds graph from source, writes config
```

That's it. `anneal init` parses your codebase using tree-sitter, extracts functions, classes, and import relationships, and writes the graph to `.anneal/graph.db`. Then point your MCP client at `anneal-server` and you're ready to go.

## How It Works

1. **Build graph** — `anneal init` walks your source tree and extracts structural relationships via tree-sitter, supporting 20+ languages (Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, C/C++, and more)
2. **Generate candidates** — keyword matching + graph topology identify relevant chunks
3. **Formulate QUBO** — minimize token cost, maximize relevance, reward dependency coverage
4. **Solve via simulated annealing** — SpinChain engine finds optimal selection
5. **Return results** — stability-ranked, dependency-ordered chunks within your token budget

## Benchmark Results

Evaluated on 10 coding tasks against Anneal's own codebase (247 nodes, 39 files), comparing QUBO optimization against three baselines:

```
Method                 Recall  Precision       F1    Util%  Perfect
-------------------------------------------------------------------
anneal_qubo            66.7%     15.2%   24.2%   34.6%     4/10
top_k_relevance        70.0%     11.9%   20.2%   99.9%     4/10
top_k_tokens           76.7%      6.5%   11.9%   98.8%     5/10
random                 65.0%      7.1%   12.7%   99.9%     2/10
```

**Key finding:** Anneal QUBO achieves the **best F1 score (24.2%)** and **best precision (15.2%)** while using only **34.6% of the token budget** — 3x more token-efficient than baselines that fill the entire budget. The QUBO formulation selects fewer, more targeted chunks rather than brute-forcing coverage.

Run the benchmark yourself:
```bash
cd your-project
anneal init
uv run python -m benchmarks
```

## Requirements

- Python 3.11+

## Installation

```bash
pip install anneal-context
```

Or with uv:
```bash
uv tool install anneal-context
```

## Setup

### Primary: `anneal init`

```bash
cd your-project
anneal init          # builds graph from source, writes config
```

`anneal init` uses tree-sitter to parse your codebase directly — no external tools required. It supports 20+ languages including Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, C/C++, C#, Kotlin, Swift, Scala, PHP, and more.

The command:
- Walks your source files
- Extracts functions, classes, and import relationships
- Builds `.anneal/graph.db`
- Writes a default `.anneal/config.toml`

Add `.anneal/` to your `.gitignore`.

### Optional: Advanced Graph Sources

If you have [code-review-graph](https://github.com/nicholasgasior/code-review-graph) or [Graphify](https://github.com/safishamsi/graphify) installed, Anneal merges their graph data alongside the built-in tree-sitter graph. This can provide additional structural signals (e.g., review history from code-review-graph, or Claude-generated summaries from Graphify).

```bash
# code-review-graph
npx code-review-graph install

# Graphify (Claude Code)
/plugin marketplace add safishamsi/graphify && /graphify
```

### Configuration

Default config is written by `anneal init`. You can customize `.anneal/config.toml`:

```toml
[budget]
default_tokens = 5000
strategy = "balanced"   # "minimal" | "balanced" | "thorough"

[solver]
backend = "simulated-annealing"
num_reads = 100
num_sweeps = 1000
```

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
