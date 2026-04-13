# Anneal — Gemini CLI Setup

## Installation

```bash
pip install anneal-context
```

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

## Usage

```
@anneal get_optimal_context task_description="add unit tests for auth module"
```
