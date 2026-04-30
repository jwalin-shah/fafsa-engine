# Deployment

## Modal (recommended — $0 idle, ~$0.001/query with Claude)

One-time setup:

```bash
uv pip install modal
modal token new            # browser auth
modal secret create fafsa-llm-keys ANTHROPIC_API_KEY=<your-key>
```

Local dev (auto-reload, ephemeral URL):

```bash
modal serve app.py
```

Production deploy (persistent URL):

```bash
modal deploy app.py
```

Modal will print three URLs (one per `@modal.fastapi_endpoint`):
- `https://<workspace>--fafsa-engine-index.modal.run/`        — HTML form
- `https://<workspace>--fafsa-engine-sai.modal.run/`          — POST endpoint
- `https://<workspace>--fafsa-engine-health.modal.run/`       — health check

Test:

```bash
curl -X POST https://<workspace>--fafsa-engine-sai.modal.run/ \
  -H 'content-type: application/json' \
  -d '{"query": "My parents make $80k, family of 4"}'
```

## Costs

Claude Haiku 3.5 backend: ~$0.001 per query, $0 idle. Modal compute is free below the monthly tier for short-lived requests like this.

## Switching backends

`POST /sai` accepts `{"query": "...", "backend": "claude" | "openai"}`. To add Ollama or MLX, you'd need GPU compute (~$0.20/hr while warm) — not recommended for a public demo.

## Secrets

Modal secret `fafsa-llm-keys` should contain at least `ANTHROPIC_API_KEY`. Add `OPENAI_API_KEY` if you want OpenAI fallback.
