---
name: Polymarket World Cup slug construction
description: How to build Polymarket fifwc event slugs reliably from the local match schedule
---

# Polymarket fifwc slug quirks

Polymarket World Cup 2026 event slugs look like `fifwc-{home}-{away}-{YYYY-MM-DD}`,
but two things break naive construction from `football.matches.json`:

1. **Team codes are mostly FIFA but NOT always.** Some teams use the ISO 3166-1
   alpha-3 code instead. Confirmed: Switzerland is `che` (ISO), not `sui` (FIFA).
   But Haiti (`hai`), Paraguay (`par`) stay FIFA. There is no clean rule — it is
   per-team inconsistent.

2. **The slug date is the stadium-local UTC date, which can differ by ±1 day**
   from our schedule's `local_date`. Two matches both at "21:00" can land on
   different UTC dates because WC2026 spans multiple US/CA/MX timezones.
   Example: Australia vs Türkiye is `06/13` locally but `fifwc-aus-tur-2026-06-14`.

**How to apply:** Don't trust a single constructed slug. Try the FIFA code first,
then an ISO fallback (see `FIFA_TO_ISO` in `backend/main.py`), and try the base
date plus ±1 day. Take the first slug that returns an event. This is what
`find_polymarket_event()` does.

**Why:** A missing match is almost never "Polymarket doesn't have it" — it's
usually a wrong code (SUI vs CHE) or an off-by-one UTC date. Verify with the
gamma public-search endpoint before concluding a market doesn't exist.
