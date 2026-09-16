# Datadog Observability & Evaluation Setup Guide

This document describes the Datadog observability instrumentation and evaluation harness added to the MovieRec backend.

## ⚠️ PRIVACY WARNING

**When Datadog LLM Observability is enabled, the following data is transmitted to Datadog:**
- Full user queries (e.g., "something slow and melancholic")
- Complete LLM prompts including movie titles, overviews, and keywords
- LLM responses with recommendations and reasons
- Token counts and cost estimates

**This data includes:**
- User input that may contain personal preferences or sentiment
- Movie metadata from your database
- LLM-generated text

**Before enabling in production:**
1. Review your privacy policy to ensure compliance
2. Consider user consent requirements for third-party data transmission
3. Evaluate data residency requirements (Datadog site: `datadoghq.com`)
4. Implement appropriate PII scrubbing if needed
5. Consider disabling LLM Observability (`DD_API_KEY` unset) if data transmission is a concern

**To disable data transmission entirely:**
- Omit `DD_API_KEY` or set `DD_TRACE_ENABLED=false`
- Application runs normally without any Datadog integration

---

## Overview

The implementation follows the observability plan outlined in `architecture.md`:
- **LLM Observability** (agentless) tracks token counts, costs, and latency for Claude Haiku calls
- **Custom spans** instrument embedding, vector search, and LLM reranking operations  
- **Trace filtering** limits observability to `/recommend` endpoint only
- **Evaluation harness** provides systematic quality testing of recommendations

**Note**: When using agentless LLM Observability mode (recommended for production), traditional APM tracing is disabled. LLM Observability provides comprehensive request-level visibility without requiring a Datadog agent.

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
DD_TRACE_ENABLED=false                 # Enable observability (default: false - opt-in required)
DD_API_KEY=your_datadog_api_key_here   # Required when DD_TRACE_ENABLED=true for LLM Observability
DD_SERVICE=movie-rec-backend           # Service name in Datadog (default shown)
DD_ENV=dev                             # Environment: dev, staging, production (default: dev)
DD_VERSION=1.0.0                       # Optional: version tag for this deployment
DD_TRACE_AGENT_URL=                    # Optional: custom agent URL (advanced use only)
```

### Obtaining a Datadog API Key

1. Sign up at [datadoghq.com](https://www.datadoghq.com/)
2. Navigate to **Organization Settings → API Keys**
3. Create a new API key or copy an existing one
4. Add it to your `.env` file as `DD_API_KEY`

**Important**: The application runs normally without Datadog. Observability is **opt-in** (set `DD_TRACE_ENABLED=true` and provide `DD_API_KEY`).

## Running with Datadog Observability

### Observability Modes

**Agentless LLM Observability (Recommended for Production)**:
- Set `DD_TRACE_ENABLED=true` and provide `DD_API_KEY`
- Uses agentless mode (data sent directly to Datadog, no local agent required)
- Captures LLM calls, token usage, costs, and latency
- Traditional APM tracing is **disabled** in this mode (only LLM Observability is active)
- TraceFilter is not used (no agent to filter)

**Agent-based APM (Advanced/Local Development Only)**:
- Requires local Datadog agent running on port 8126
- Set `DD_TRACE_ENABLED=true` and `DD_TRACE_AGENT_URL=http://localhost:8126`
- Omit `DD_API_KEY` to use agent-only mode
- Not recommended for production (use agentless mode instead)

### Local Development with LLM Observability

Start the FastAPI server with Datadog observability enabled:

```bash
cd backend
export DD_TRACE_ENABLED=true
export DD_API_KEY=your_key_here
uvicorn app.main:app --reload
```

**Note**: The Procfile automatically wraps the server with `ddtrace-run` when deployed with `DD_TRACE_ENABLED=true` AND `DD_API_KEY` set. For local development, `ddtrace-run` is optional (the instrumentation initializes at startup either way).

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

Per the architecture plan, observability is scoped to **`/recommend` requests only**. Health checks (`/health`) and static assets do not generate observability data.

**Important**: The `TraceFilter` that filters by endpoint is only active in **agent-based APM mode** (advanced/local development). In the recommended **agentless LLM Observability mode** (production), the tracer is disabled (`enabled=False`), so the TraceFilter is not used. Instead, LLM Observability naturally captures only `/recommend` because that's the only endpoint that calls `wrap_llm_call()`.

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

Each test query is evaluated on five criteria (all must pass):

1. **Result count**: Must return at least `min_results` (default: 3)
2. **Genre diversity**: Number of unique genres in results (must be > 0)
3. **Expected genre matching**: At least 1 genre from `expected_genres` must appear in results
4. **Average rating**: Mean `vote_average` across results (must be ≥ 6.0)
5. **Reason quality**: Average reason length must be ≥ `min_reason_length` (default: 20 characters)

**Example**:
```python
EvalQuery(
    query="a lighthearted comedy for Friday night",
    expected_genres=["Comedy"],  # At least one must match
    min_results=3,
    min_reason_length=20,
)
```

### Test Query Coverage

The 8 test queries cover:
- Emotional/mood-based requests ("something slow and melancholic")
- Scenario-based requests ("Friday night with friends")
- Genre + mood combinations ("mind-bending sci-fi")
- Artistic characteristics ("visually stunning with minimal dialogue")
- Audience-specific requests ("heartwarming family movie")

Each query defines `expected_genres` that must match at least one result genre, preventing irrelevant recommendations (e.g., Horror results for a Comedy query would fail).

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

1. Set environment variables:
   ```bash
   DD_TRACE_ENABLED=true
   DD_API_KEY=your_production_key
   DD_ENV=production
   DD_VERSION=1.0.0
   DD_SERVICE=movie-rec-backend
   ```

2. The Procfile automatically uses `ddtrace-run` when **both** `DD_TRACE_ENABLED=true` AND `DD_API_KEY` are set:
   ```bash
   # From backend/Procfile
   web: if [ "$DD_TRACE_ENABLED" = "true" ] && [ -n "$DD_API_KEY" ]; then 
     ddtrace-run uvicorn app.main:app --host 0.0.0.0 --port $PORT
   else 
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
   fi
   ```

3. Monitor the Datadog LLM Observability dashboard for token usage, costs, and latency

**Note**: Agentless mode is used in production (no Datadog agent required). Traditional APM metrics are not available; use LLM Observability for request-level visibility.

## Cost Considerations

- **Datadog APM**: Free tier includes 1M spans/month
- **Datadog LLM Observability**: Included in APM; no additional cost
- **Scoped tracing**: Only `/recommend` requests generate traces, keeping usage within free tier for demo/low-traffic apps

## Troubleshooting

### "DD_API_KEY not set" Warning

This is expected if you haven't configured Datadog. The application runs normally without observability.

To enable observability:
1. Set `DD_TRACE_ENABLED=true` in `.env`
2. Add `DD_API_KEY=your_key` to `.env`
3. Restart the application

### No Data in Datadog

1. Verify **both** `DD_TRACE_ENABLED=true` and `DD_API_KEY` are set
2. Make a request to `/recommend` (not `/health`, which is not traced)
3. Check Datadog **LLM Observability** dashboard (not APM - agentless mode uses LLM Observability only)
4. Allow 1-2 minutes for data to appear

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
