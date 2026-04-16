# Anneal

Optimal code context selection for AI coding assistants. Parses your codebase into a structural graph, formulates chunk selection as a QUBO problem, and solves for the minimum context set within a token budget.

```bash
pip install anneal-context
cd your-project
anneal init
```

## The Problem

When an AI coding assistant starts a task, it needs to find the right code. Current approaches — keyword search, embedding similarity, greedy top-k — evaluate files independently. They can't jointly optimize for relevance, dependency coverage, and redundancy within a budget.

Anneal treats context selection as a combinatorial optimization problem. It builds a structural graph of your codebase (functions, classes, imports, call relationships), scores candidates against your task, and solves a QUBO to find the optimal subset — not just the individually best files, but the best *set* of files.

## Results

Evaluated on 10 coding tasks (247 nodes, 39 files):

| Method | Recall | Precision | F1 | Perfect |
|--------|--------|-----------|------|---------|
| **Anneal (QUBO)** | **66.7%** | **13.5%** | **22.2%** | **4/10** |
| Top-k relevance | 53.3% | 9.9% | 16.5% | 2/10 |
| Top-k tokens | 75.0% | 7.0% | 12.7% | 6/10 |
| Random | 55.0% | 6.9% | 12.2% | 2/10 |

**Best F1 (22.2%)** — 35% above the next baseline. Nearly **2x precision** of any greedy method. Top-k-by-tokens achieves higher raw recall by packing more chunks, but QUBO's joint optimization produces more targeted selections.

**Latency:** 0.3s (10K LOC), 0.8s (50K LOC), 1.35s (100K LOC). The QUBO solve stays flat at ~0.23s — candidate capping bounds the problem size.

## How It Works

1. **Graph construction** — `anneal init` parses source files with tree-sitter, extracts functions, classes, and import relationships into `.anneal/graph.db`
2. **Candidate scoring** — Keyword matching (85%) + graph centrality (15%) identify top candidates + neighbors (capped at 200)
3. **QUBO formulation** — Relevance reward, token cost penalty, dependency coupling, redundancy repulsion, budget constraint
4. **Simulated annealing** — SpinChain's SA solver finds the optimal selection
5. **Safety net** — Hard budget trim guarantees token compliance

```
Linear:    w_i = -mu * relevance + alpha * token_cost + penalty * budget_violation
Quadratic: w_ij = gamma * redundancy - beta * dependency + penalty * budget_interaction
```

Three pre-tuned strategies:

| Strategy | Budget | Use case |
|----------|--------|----------|
| `minimal` | ~2K tokens | Quick lookups, small fixes |
| `balanced` | ~5K tokens | Everyday development |
| `thorough` | ~10K tokens | Complex multi-module changes |

## Setup

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

### Any MCP Client

Run `anneal-server` via stdio transport.

## Tools

### get_optimal_context

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_description` | str | required | What you want to do |
| `token_budget` | int | 5000 | Max tokens to return |
| `include_files` | list[str] | [] | Always include these paths |
| `exclude_files` | list[str] | [] | Never include these paths |
| `strategy` | str | "balanced" | "minimal", "balanced", or "thorough" |

Returns stability-ranked, dependency-ordered chunks with relevance scores and a dependency graph.

### get_status

Returns graph source availability, node counts, and solver configuration.

## Configuration

`anneal init` writes `.anneal/config.toml`:

```toml
[budget]
default_tokens = 5000
strategy = "balanced"

[solver]
backend = "simulated-annealing"
num_reads = 100
num_sweeps = 1000
```

Add `.anneal/` to your `.gitignore`.

## Language Support

Tree-sitter parsing supports 20+ languages: Python, JavaScript, TypeScript, Go, Rust, Java, Ruby, C, C++, C#, Kotlin, Swift, Scala, PHP, and more.

## Benchmarking

```bash
cd your-project
anneal init
uv run python -m benchmarks
```

Compares QUBO selection against top-k-by-relevance, top-k-by-tokens, and random baselines across 10 coding tasks with ground-truth required files.

## Development

```bash
git clone https://github.com/ameyakhot/anneal
cd anneal
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
uv run pytest tests/ -v
```

## Related

**[SpinChain](https://github.com/ameyakhot/spinchain)** — The QUBO/SA optimization engine that powers Anneal. Also provides reasoning chain verification for LLM outputs.

Anneal optimizes the **input** (what code the LLM sees). SpinChain optimizes the **output** (reasoning quality). Same engine, different formulations.

## License

MIT
