---
name: flight-search
description: Search and compare flights using the Fli CLI. Use for exact or flexible travel dates, cheapest date pairs, nearby airports, and family or group fares. Ask for missing trip details and recheck shortlisted fares. For flight research only.
compatibility: Requires terminal access, the fli CLI from the Python flights package, and internet access.
---

# Flight search

Use `fli` to find and compare Google Flights quotes. Return a shortlist the user
can check and book themselves.

## Gather the trip details

Reuse details from the conversation. On a follow-up such as “also add Monday,”
keep the other constraints and search the newly eligible dates. Group missing
details into one short question before running a fare search:

- **Route:** Departure and destination cities or airports. If the destination is
  intentionally open, ask which cities or airports to compare or offer a small
  set for the user to confirm.
- **Dates:** One-way or round trip if unclear. Ask for exact dates or a flexible
  window. For a flexible round trip, ask for the earliest departure, latest
  return, and acceptable nights if they aren't specified. Resolve ambiguous years
  or date boundaries before searching.
- **Travelers:** Ask how many adults are flying and the ages of any children at
  travel time. For infants under 2, ask whether they will sit on a lap or in their
  own seat. If someone changes fare age category during the trip, flag it for
  airline verification rather than guess.

Use economy unless requested otherwise. Use the user's preferred currency or
state the currency you choose. Ask about budget, bags, stops, nearby airports,
or time of day only when the answer changes the search materially. Treat stated
requirements as filters and preferences as ranking criteria.

## Search with Fli

Check `command -v fli`. If it's missing or lacks the flags needed for the search,
read [Install and verify Fli](references/install.md). Use the installed command's
`--help` to resolve version differences. If `fli` cannot run, report the blocker
and give the setup steps. All fare searches in this skill require the CLI.

1. **Resolve airports.** Use `fli airports "Warsaw"` when available. Resolve city
   names to IATA airport codes. Include practical alternatives for a city-level
   request, but respect explicitly requested airports. Name the actual airports
   in the results so the user can compare ground transfers.
2. **Set fare inputs.** Use `--passengers` for adults, `--children` for ages
   2–11, and `--infants-on-lap` or `--infants-in-seat` for under 2. Carry the
   same passenger mix, currency, cabin, and applicable filters through every
   search and recheck. Use `--stops 0` for nonstop-only searches.
3. **Choose the search.** Use `fli flights` for exact dates and include
   `--return` for a round trip. For flexible dates, use `fli dates` per airport
   pair and, for round trips, per allowed number of nights. Treat `--to` as the
   latest departure searched: cap it at the latest allowed return minus the
   trip length, then verify every returned date pair against the original
   window and night count. Split large date ranges into supported chunks. If
   mixing outbound and return airports is acceptable, check promising date pairs
   with comma-separated airport codes where the installed CLI supports them.
4. **Recheck the shortlist.** Run `fli flights` on the best date pairs before
   quoting them. Read the actual airport, airline, stops, and local times for
   both directions. If the price changes, use the exact-date result. If a date
   pair can't be rechecked, label it a date-search estimate. Treat provider errors
   and empty results as unverified coverage, not proof that no flights exist.

Example commands for two adults and one child. Replace airports, dates, and
options with the trip details; omit `--return` for a fixed-date one-way flight.

```bash
fli dates BCN WMI --from 2026-12-14 --to 2026-12-25 \
  --round --duration 7 --passengers 2 --children 1 --stops 0 \
  --currency EUR --country ES --sort --format json

fli flights BCN WMI 2026-12-14 --return 2026-12-21 \
  --passengers 2 --children 1 --stops 0 --currency EUR --country ES \
  --format json
```

## Present the shortlist

Lead with the cheapest result found and the best fit if they differ. Explain
the practical tradeoff, such as a late arrival, farther airport, or short stay.
For each option show dates, nights for round trips, airline, airport codes,
local times, stops, and the quoted total for the whole party. Link dated Google
Flights results and mention that links may need the traveler counts set again.
State when you checked the quotes and flag any material search gaps. Baggage,
seats, and the final total must be verified at checkout unless already confirmed.
