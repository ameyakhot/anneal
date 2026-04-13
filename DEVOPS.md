# Anneal DevOps

Full DevOps documentation lives in the SpinChain repo:
`spinchain/docs/superpowers/specs/2026-04-13-devops-workflow.md`

It covers the complete workflow for both SpinChain and Anneal:
- Project architecture and relationship
- Local development setup
- CI/CD pipelines
- Release and publish process
- Cross-repo dependency management
- PyPI trusted publisher setup

## Quick Reference

| Item | Value |
|------|-------|
| PyPI name | `anneal-context` |
| Import name | `anneal` |
| Entry point | `anneal-server` |
| Depends on | `spinchain>=0.1.0` |
| CI | `.github/workflows/ci.yml` — test + lint + SpinChain canary |
| Publish | `.github/workflows/publish.yml` — triggers on GitHub Release |
| SpinChain public API | `spinchain/PUBLIC_API.md` |

## Local Dev

```bash
cd ~/quantum/anneal
source .venv/bin/activate
uv pip install -e ~/quantum/spinchain   # editable spinchain
uv pip install -e ".[dev]"
python -m pytest tests/ -v
ruff check src/ tests/
```

## Release

1. Ensure SpinChain is published to PyPI first (if new version needed)
2. Update version in `pyproject.toml`
3. `git commit`, `git tag vX.Y.Z`, `git push origin main --tags`
4. Create GitHub Release from tag → publish.yml runs automatically
