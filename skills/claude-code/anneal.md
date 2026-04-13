# Anneal — Optimal Context Selection

Use this skill to get the optimal code context before starting any task. Anneal
uses QUBO optimization over the codebase dependency graph to select the minimum
token set that maximizes task relevance.

## When to Use

Call `mcp__anneal__get_optimal_context` at the start of any coding task before
reading files. This replaces manual file discovery.

## Usage

### Get optimal context
```
mcp__anneal__get_optimal_context(
  task_description="<describe what you want to do>",
  token_budget=5000,
  strategy="balanced",
  include_files=[],
  exclude_files=[],
)
```

### Check status
```
mcp__anneal__get_status()
```

## First-Time Setup

If `get_optimal_context` returns an error about no graph sources, install one:

**code-review-graph** (recommended):
```
npx code-review-graph install
```

**Graphify:**
```
/plugin marketplace add safishamsi/graphify
/graphify
```

Then create `.anneal/config.toml` in your project root:
```toml
[budget]
default_tokens = 5000
strategy = "balanced"

[solver]
backend = "simulated-annealing"
num_reads = 100
num_sweeps = 1000
```

## Installation (Claude Code)

Add to your MCP config:
```json
{
  "mcpServers": {
    "anneal": {
      "command": "anneal-server",
      "args": []
    }
  }
}
```

Or with uvx (no install):
```json
{
  "mcpServers": {
    "anneal": {
      "command": "uvx",
      "args": ["anneal"]
    }
  }
}
```
