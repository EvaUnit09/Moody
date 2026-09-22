# Moody — frontend

React + TypeScript + Vite frontend for [Moody](../README.md).

## Commands

```bash
npm install
npm run dev          # local dev server, http://localhost:5173
npm run build         # typecheck + production build
npm run lint          # oxlint
npm test              # vitest, single run
npm run test:coverage # vitest with coverage report
```

Set `VITE_API_URL` in `.env.local` (see `.env.example`) to point at a running
backend — defaults to `http://localhost:8000`.

See the [root README](../README.md) for the full project overview and
[docs/architecture.md](../docs/architecture.md) for stack decisions.
