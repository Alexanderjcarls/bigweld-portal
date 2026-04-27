# Bigweld DA Portal

Work-augmentation chat-spine portal for the Bigweld DA. Lives at `bigweld.ninerealms.me`.

Bigweld is Alex's fourth Domain Agent, scoped to **work + work-flavored ideation only** — SFDC architect work, HPE Pointnext / Storage / GreenLake support, KB curation, deliverable drafting. Substrate is the Bigweld Neo4j second-brain at `/datapool/bigweld/`.

See the design + plan in the Oracle repo:
- Spec: `/datapool/oracle/docs/superpowers/specs/2026-04-27-bigweld-portal-design.md`
- Plan: `/datapool/oracle/docs/superpowers/plans/2026-04-27-bigweld-portal-implementation.md`

## Architecture (one paragraph)

Vite + React 19 + TS + Tailwind 4 + shadcn/ui frontend; FastAPI + uvicorn backend on EPYC `:8884`; Pattern A subprocess of `claude -p` per turn with `--resume` for continuity; filesystem JSON-canonical persistence via three Claude Code hooks (`UserPromptSubmit`, `PostToolUse`, `Stop`); DeepInfra Qwen3-235B summarizer via Aegis V2 router pattern. Auth via Cloudflare Access (single-user). Bigweld DA's CWD is this repo; substrate read-only via Bash + cypher-shell to Neo4j on `127.0.0.1:7687`.

## Run locally

```bash
# Backend
cd backend && uv run uvicorn main:app --reload --port 8884

# Frontend
cd frontend && npm run dev
```

## Layout

- `/CLAUDE.md` — Bigweld DA's identity (loaded by `claude -p`)
- `/memory/` — persona, working-with-alex, world-model, never-list
- `/skills/` — chat-time skill library (graph, gaps, orphans, rollup, dupes, citations, search-past-conversations)
- `/.claude/` — hook config + scripts
- `/backend/` — FastAPI + subprocess manager + stream parser + summarizer
- `/frontend/` — Vite + React + TS SPA
- `/scripts/` — palette extraction, font conversion, deploy helpers
- `/conversations/` — runtime data (gitignored)
- `/output/` — runtime artifacts (gitignored)
