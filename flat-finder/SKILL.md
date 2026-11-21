---
name: flat-finder
description: Research rental homes with saved requirements, source-linked costs, commute checks and conversation-aware follow-up in Codex. Use for an actual rental search or updating its shortlist, not for buying property or contacting unrelated leads.
---

# Flat Finder

Help the user find a suitable rental, not merely collect ads. Use the user's latest
requirements and existing authorizations. The included Python helpers validate,
assess and display saved evidence; they do not perform live searches or send messages.

## Start from the actual context

Find the project's current profile, contact ledger, receipts, holds and coordination
contract. Reconcile newer direct user corrections before old templates. Preserve
campaign separation, sender ownership and consumed actions. Never overwrite an
existing project's canonical files with an example profile.

For a new search, establish only missing material facts: city/areas, accepted home
types, personal rent-plus-maintenance cap (strict or inclusive), an explicit dated
move-in deadline, timezone, commute anchors and exclusions. Private-room exceptions
can have narrower anchor requirements than entire flats. References are clues, not
an exhaustive whitelist or a license to search an excluded locality.

Save real data in a private workspace **outside the skill and public repository**.
Read [the data contract](references/data-contract.md) when creating or importing
records. Use the bundled example as schema guidance, never as real listings.

```sh
python3 <skill-dir>/scripts/flat_finder.py init --workspace <private-dir> --profile <profile.json>
python3 <skill-dir>/scripts/flat_finder.py plan --workspace <private-dir>
```

## Research and verify

Use available web search and the user's actual supported signed-in browser. A login
failure in another session does not establish failure in that browser. Reuse your
own task tab, preserve other chats' tabs and close completed own tabs. Security
prompts, login and history-restoration steps belong to the user. Do not bypass them
or repeatedly ask an unchanged access question. Continue independent safe work.

Respect source priority. If Facebook is preferred, search exact apartment-name
variants, streets, gate neighborhoods and room/flat phrasing there. Supplement with
rental portals, direct property sites and web results. Cross-match the exact building,
photos, cost, provider and map point; matching locality text alone is insufficient.
Never call an index search result an inspected current post, or assume a portal
listing is also on Facebook. Record source coverage and access gaps explicitly.

For each promising lead, capture the exact permalink, source-check timestamp,
listing facts, rent, maintenance (unknown stays unknown), deposit, brokerage and
setup separately. An advertised vacancy date is not current provider confirmation.
Do not invent a rolling deadline or silently widen a budget, area or housing type.
An expired deadline requires one updated-window question, not stale outreach.

Map actual property entrances against independently verified usable commute anchors.
Keep straight-line radius separate from a practical walking route. Record map-link
provenance, route date, exact-entrance precision and restrictions/access uncertainty.
Do not infer pedestrian access from two nearby POIs, or a building name from a fuzzy
map hit. Only mark a route verified when the evidence actually supports it.

Deduplicate exact source URLs, provider identity, phone, property and prior messages
across platforms. Keep distinct units distinct unless evidence proves a duplicate.
Do not silently merge uncertain identities. Read full available current chains,
not only unread flags or previews. Mark unreviewed separately from unchanged.

## Contact only within authority

The viewer is read-only. In Codex, use the user's existing explicit standing scope
when it covers the action; do not ask again for already-authorized routine actions.
Otherwise prepare the exact recipient/text and obtain authorization before sending.
The skill itself grants no authority to accept requests, message, post or book.

Before each send, verify the actual sender account, exact recipient, source and full
available history; reconcile the latest ledger/owner and acquire its durable contact
claim. Never race another sender. Preserve closed/not-interested, held, unanswered
sent and unknown-delivery states across channels. Do not nudge or retry a consumed
request just because an ad is reimported. A genuine new substantive reply can create
a new contextual action after those checks; do not bulk-reset contact status.

Ask one useful missing-information question at a time. Request an owner's/provider's
contact privately when appropriate. A public phone, platform helpline or broker
number is not proof of property ownership or a verified WhatsApp recipient. Normalize
numbers with a confirmed country context; keep provenance and role. Introduce the
actual source accurately on a new channel; do not invent Facebook provenance.
Never publish private phone numbers, profiles, messages or housing media.

Do not infer gender from a name, photo or profile. Apply an explicit incoming-occupant
confirmation rule only when the user's private shared-home campaign requires it;
that rule does not apply to providers offering the user an entire flat. Keep any
replacement campaign's media allowlist separate from the user's home search.

Verify the visible post-send result. Distinguish prepared, attempted, Sent, Delivered
and Read. Unknown outcome stays unknown until reconciled. Do not book visits/calls,
change calendars, pay, negotiate binding tenancy terms or publish without the
specific applicable authority. Record proposed times as unconfirmed when necessary.

## Update the shortlist and deliver

```sh
python3 <skill-dir>/scripts/flat_finder.py import --workspace <private-dir> --input <checked-listings.json>
python3 <skill-dir>/scripts/flat_finder.py report --workspace <private-dir>
python3 <skill-dir>/scripts/flat_finder.py serve --workspace <private-dir> --port 43126
```

Use the provided `workspace_lock` when editing the helper's dataset; follow any
stronger project-wide writer contract before touching canonical state. Import is
atomic and preserves held/closed/unavailable and protected contact states. It does
not establish the truth of an input receipt. Recheck the original source/history.

Open the resulting loopback URL using the supported local-web-development browser
workflow and verify the rendered output. Give the user a clickable on-screen result,
not just a TSX/source path. Include a concise source-linked table in chat if requested.
Lead with real confirmed matches; label provisional candidates and their gaps.
Report actual searches, sends and remaining blockers honestly; do not claim that a
plan, app build, schedule or imported dataset completed the housing search.

For public demos use only bundled synthetic data: `serve --demo`. Never publish or
share the private viewer. The release packager only exports the synthetic fixture.
