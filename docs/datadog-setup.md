# Datadog Observability & Evaluation Setup Guide

This document describes the Datadog observability instrumentation and evaluation harness added to the MovieRec backend.

## Overview

The implementation follows the observability plan outlined in `architecture.md`:
- **APM tracing** via `ddtrace-run` wraps the FastAPI application
- **Custom spans** instrument embedding, vector search, and LLM reranking operations
- **LLM Observability** tracks token counts, costs, and latency for Claude Haiku calls
- **Evaluation harness** provides systematic quality testing of recommendations

## Architecture

### Observability Components

1. **`app/services/observability.py`**: Core instrumentation service
   - `DatadogObservability` class with static methods for tracing
   - Custom decorators for embedding, vector search, and LLM operations
   - LLM Observability integration for token/cost tracking

2. **Instrumented Services**:
   - `app/services/embeddings.py`: Traces OpenAI embedding calls
   - `app/db.py`: Traces Supabase pgvector similarity searches
   - `app/services/rerank.py`: Traces Claude Haiku reranking with LLM Observability

3. **Configuration**:
   - `app/config.py`: Datadog-specific settings (API key, service name, environment)
   - `app/main.py`: Initializes Datadog at startup

### Evaluation Components

1. **`app/services/eval.py`**: Evaluation framework
   - `EvaluationHarness` class for systematic quality testing
   - 8 curated test queries covering different moods and scenarios
   - Metrics: result count, genre diversity, average rating, pass/fail

2. **`app/scripts/run_eval.py`**: Evaluation runner script
   - Runs full evaluation suite
   - Outputs summary with pass rate and aggregate metrics
   - Supports JSON output for automated parsing

## Configuration

### Environment Variables

Add the following to your `backend/.env` file:

```bash
# Required - existing variables
OPENAI_API_KEY=sk-...
SUPABASE_DB_URL=postgresql://...
ANTHROPIC_API_KEY=sk-ant-...

# Datadog configuration (new)
DD_API_KEY=your_datadog_api_key_here  # Optional, but required for LLM Observability
DD_SERVICE=movie-rec-backend           # Service name in Datadog
DD_ENV=dev                             # Environment (dev, staging, production)
DD_VERSION=1.0.0                       # Optional: version tag for this deployment
DD_TRACE_ENABLED=true                  # Enable/disable tracing (default: true)
```

### Obtaining a Datadog API Key

1. Sign up at [datadoghq.com](https://www.datadoghq.com/)
2. Navigate to **Organization Settings → API Keys**
3. Create a new API key or copy an existing one
4. Add it to your `.env` file as `DD_API_KEY`

**Note**: The application will run without `DD_API_KEY`, but LLM Observability features will be disabled. APM tracing via `ddtrace-run` will still work for basic request/response tracing.

## Running with Datadog APM

### Local Development

Start the FastAPI server with Datadog APM instrumentation:

```bash
cd backend
ddtrace-run uvicorn app.main:app --reload
```

The `ddtrace-run` command automatically instruments FastAPI, asyncpg, and HTTP clients.

### Custom Spans

Three custom spans are automatically added to the `/recommend` endpoint:

1. **`embedding.generate`**
   - Resource: `openai.text-embedding-3-small`
   - Tags: model, provider, input length, embedding dimension

2. **`vector_search.similarity`**
   - Resource: `supabase.pgvector`
   - Tags: provider, index type (HNSW), similarity metric (cosine), limit, result count

3. **`llm.rerank`**
   - Resource: `anthropic.claude-haiku-4-5`
   - Tags: provider, model, operation, query length, candidate count, output count
   - LLM Observability: input/output tokens, cost estimate

### Trace Filtering

Per the architecture plan, tracing is scoped to **`/recommend` requests only**. Health checks (`/health`) and static assets do not generate traces, keeping signal-to-noise high and staying within Datadog's free tier limits.

## Running the Evaluation Harness

The evaluation harness tests recommendation quality across 8 curated mood/scenario queries.

### Basic Usage

```bash
cd backend
python -m app.scripts.run_eval
```

### Output Example

```
[Eval] Starting evaluation harness...

============================================================
EVALUATION SUMMARY
============================================================
Total queries:          8
Passed:                 8
Failed:                 0
Pass rate:              100.0%
Avg results per query:  5.4
Avg genre diversity:    3.2
Avg rating:             7.3/10
Elapsed time:           4.23s
============================================================
```

### Verbose Output

Include detailed per-query results:

```bash
python -m app.scripts.run_eval --verbose
```

### JSON Output

For automated parsing or CI integration:

```bash
python -m app.scripts.run_eval --json
```

### Exit Codes

- `0`: All queries passed (100% pass rate)
- `1`: One or more queries failed

## Evaluation Metrics

Each test query is evaluated on:

1. **Result count**: Must return at least `min_results` (typically 3-5)
2. **Genre diversity**: Number of unique genres in results
3. **Average rating**: Mean `vote_average` across results (must be ≥6.0)
4. **Reason quality**: Each result must include a query-specific reason

### Test Query Coverage

The 8 test queries cover:
- Emotional/mood-based requests ("something slow and melancholic")
- Scenario-based requests ("Friday night with friends")
- Genre + mood combinations ("mind-bending sci-fi")
- Artistic characteristics ("visually stunning with minimal dialogue")
- Audience-specific requests ("heartwarming family movie")

## Datadog Dashboard Metrics

Once tracing is active, the following metrics are available in Datadog:

### APM Metrics
- **Requests/min**: Total `/recommend` request rate
- **p50/p95/p99 latency**: Request latency percentiles
- **Error rate**: Percentage of requests returning 4xx/5xx

### Custom Span Metrics
- **Embedding latency**: Time spent in OpenAI embedding calls
- **Vector search latency**: Time spent in pgvector similarity search
- **LLM rerank latency**: Time spent in Claude Haiku reranking

### LLM Observability Metrics
- **Token count**: Input/output tokens per LLM call
- **Cost per request**: Estimated cost based on Anthropic pricing
- **Cost per day**: Aggregate daily cost projection
- **Model performance**: Claude Haiku-specific latency and error tracking

## Integration with CI/CD

### Running Evals in CI

Add the evaluation harness to your CI pipeline to catch regressions:

```yaml
# Example GitHub Actions workflow
- name: Run evaluation harness
  run: |
    cd backend
    python -m app.scripts.run_eval --json > eval-results.json
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    SUPABASE_DB_URL: ${{ secrets.SUPABASE_DB_URL }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    DD_TRACE_ENABLED: false  # Disable tracing in CI
```

### Datadog in Production

For production deployments (e.g., Railway):

1. Add `DD_API_KEY`, `DD_ENV=production`, and `DD_VERSION` as environment variables
2. Ensure the start command uses `ddtrace-run`:
   ```
   ddtrace-run uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
3. Monitor the Datadog dashboard for request volume, latency, and LLM costs

## Cost Considerations

- **Datadog APM**: Free tier includes 1M spans/month
- **Datadog LLM Observability**: Included in APM; no additional cost
- **Scoped tracing**: Only `/recommend` requests generate traces, keeping usage within free tier for demo/low-traffic apps

## Troubleshooting

### "DD_API_KEY not set" Warning

This is expected if you haven't added a Datadog API key yet. Basic APM tracing via `ddtrace-run` will still work; only LLM Observability features require the API key.

### No Traces in Datadog

1. Verify `DD_TRACE_ENABLED=true` in your `.env`
2. Check that you're starting the app with `ddtrace-run`
3. Make a request to `/recommend` (not `/health`)
4. Allow 1-2 minutes for traces to appear in Datadog

### Eval Harness Fails

Common causes:
- Missing environment variables (`OPENAI_API_KEY`, etc.)
- Empty or incomplete database (`select count(*) from movies;` should return >0)
- Network issues connecting to OpenAI, Anthropic, or Supabase

## References

- Architecture document: `docs/architecture.md`
- Datadog APM docs: https://docs.datadoghq.com/tracing/
- Datadog LLM Observability: https://docs.datadoghq.com/llm_observability/
- `ddtrace` Python library: https://ddtrace.readthedocs.io/
