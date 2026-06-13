---
name: Autoscale + SQLite causes data loss
description: Why this app must use Postgres (DATABASE_URL), not local SQLite, and how startup refresh must behave
---

# Data persistence on autoscale deployments

This project deploys as **autoscale**. Autoscale containers are ephemeral and
there can be multiple concurrent instances. A local SQLite file
(`sqlite:///./...db`) is therefore fatal: it is wiped on every container
recreation/redeploy and is NOT shared between instances. Symptom reported by the
user: "people voted, then I couldn't log in and lost data" — accounts + votes
vanished on redeploy.

**Rule:** persistent data (users, votes) MUST live in the Replit-managed
PostgreSQL (`DATABASE_URL`), never local SQLite. `backend/database.py` reads
`DATABASE_URL` (normalizing `postgres://`→`postgresql://`) and only falls back to
SQLite for local dev. Driver: `psycopg2-binary`.

**Startup refresh rules (learned the hard way):**
- The daily market refresh must NEVER delete `Market`/`VoteRecord` rows — that
  destroys votes. Upsert by `market_id` (update odds/title, insert new) so market
  ids and their votes survive.
- `markets.market_id` has a UNIQUE index so concurrent instances can't create
  duplicate markets that split votes.
- `startup_event()` runs on every instance. Guard the refresh + SharedFund init
  with a Postgres advisory lock (`pg_try_advisory_lock`) so only one instance
  does it at a time.

**Why:** all three failures (ephemeral storage, delete-on-refresh, multi-instance
races) independently destroy the vote/account data this app exists to keep.
