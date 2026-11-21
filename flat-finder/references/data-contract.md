# Local data contract (v1)

Python 3.10+ on macOS/Linux. No pip packages or API keys. Schema examples are in
`assets/examples/`; scripts accept JSON, not executable config. Unknown input keys
are dropped by normalization. Keep private workspaces outside this package.

`profile.json`: required `city`, `monthly_limit`, `move_in_before` (exclusive
YYYY-MM-DD deadline). Optional `name`, `currency` (ISO code), `timezone` (IANA,
default UTC), `strict_monthly_limit` (default true), `prefer_radius_m` (1000),
`max_radius_m` (2000), `freshness_hours` (48), `accepted_kinds`, `excluded_areas`,
`held_source_urls`, `source_priority`, `search_terms`, `references`, `unverified_anchors`,
`room_anchor_ids`. `anchors` contain id/name/lat/lng, `verified`, `access_confirmed`,
`source_url`. Do not mark a map point verified without its inspected source.

Kinds: `entire_flat`, `female_room`, `male_room`, `private_room`. Room anchors restrict
which commute entrances qualify for room leads. An unverified anchor is not a valid
radius center. A maximum radius from currently verified anchors is not a claim that
all other commute entrances have been researched.

`listings.json`: object with `listings`, `events`, `access` arrays. Each listing:

- Required: `title`, `kind`, `source_url` (exact credential-free HTTPS permalink).
  `id` defaults to a canonical-source hash. Same source reimports keep their old id.
- `source_platform`, `source_checked_at` (ISO timestamp with timezone), `area`.
- Numbers or null: `rent`, `maintenance`, `deposit`, `brokerage`, `setup_cost`,
  `size_sqft`. `maintenance_included: true` means stated rent includes maintenance.
  All costs are the user's share. Never use 0 for an unknown cost.
- `furnishing`, `advertised_availability`, `notes`. Keep dates as source claims here.
- `disposition`: active / historical / held / closed / unavailable. Historical is
  held; not an active vacancy. Held/closed/unavailable remain sticky across imports.
- `coordinates`: lat/lng, precision advertised_area / building / entrance,
  source_url. Radius uses this point, not a verified walk.
- `walk`: anchor_id, metres/minutes or null, status estimate / verified,
  exact_entrance, legitimate, source_url, checked_at, restriction_note. Verified
  assessment additionally needs an accessible verified anchor, entrance-precision
  coordinates and a fresh route check. Do not promote incomplete route evidence.
- `availability`: status unconfirmed / confirmed / unavailable, before_deadline
  bool or null, confirmed_at, evidence_url, evidence_note. Confirmed means a current
  provider statement with retained evidence, not an ad's “immediate” label.
- `contact`: phone in +country format or null, provenance_url, role (e.g. property
  provider / platform support / unverified), status none / sent / delivered / read /
  unknown / closed / held, channel, recipient_verified, history_checked_at,
  last_action_at, messenger_url, evidence_note. Do not import an attempted click as
  sent. Closed/held/unknown cannot be reset by import; sent/delivered/read cannot
  be reset to none. Existing project receipts remain the action authority.

`events`: at, title, detail, optional source_url. Keep short evidence summaries, not
raw private transcripts. `access`: channel, state, detail, checked_at. Replacing
access states is explicit; an older failure is not a new failure or a new prompt.

## Assessment and contact semantics

`ready` = all modeled evidence fields complete/fresh; not a guarantee of safety,
tenancy or successful booking. `provisional` = plausible but missing evidence.
`excluded` = violates known criteria. `held` and `closed` are protected states.
Source freshness, availability and route freshness expire. Demo data is never ready.

`can_prepare_contact` is a local triage flag, never send authorization. The full
identity, account, history, authority and sender-claim checks still happen in Codex.
A phone/recipient already protected elsewhere in the dataset also suppresses a new
first enquiry. Cross-platform identity uncertainty requires reconciliation.

## Commands

- `init --workspace DIR --profile FILE`: create once, fail rather than overwrite.
- `init --workspace DIR --demo`: initialize synthetic examples for local testing.
- `import --workspace DIR --input FILE`: merge `{listings, events?, access?}` under
  a local lock; validate the full candidate, atomically replace the dataset.
- `state --workspace DIR`: JSON with derived assessments; does not fetch sources.
- `report --workspace DIR [--format markdown|json|csv] [--include-held]`.
- `plan --workspace DIR`: query list and per-lead next actions, all search tasks
  initially unreviewed. Producing this plan does not run the queries.
- `serve --workspace DIR [--port 43126]` or `serve --demo`: read-only loopback viewer.

Local HTTP exposes only viewer assets, normalized state and explicit exports. It
never serves the workspace directory, raw profile files, arbitrary paths or browser
storage. It is for one user's local machine, not multiuser hosting. Do not tunnel
or bind it publicly. An on-device process/browser with local access can read it.
OSM basemap requests reveal the viewed geographic tile area to the tile provider;
no listing text, phone or private profile is sent by the application. Map links open
an external provider. Stop the process when the local viewer is no longer needed.
