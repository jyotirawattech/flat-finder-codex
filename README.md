# Flat Finder for Codex

A rental-search skill for Codex, with a local map and a source-linked shortlist.
Keep costs, commute evidence and conversation state together while Codex researches
with the web and browser tools available in your session.

[Try the synthetic demo](https://flat-finder-codex.pages.dev) · [Download the skill](https://github.com/jyotirawattech/flat-finder-codex/releases/download/v1.0.0/flat-finder-skill.zip) · [Release and checksums](https://github.com/jyotirawattech/flat-finder-codex/releases/tag/v1.0.0)

Inspired by the map, filters, exports and research log in [Flat Finder](https://flat-finder.pages.dev/).
This is an independent implementation. No original code, property dataset, branding
assets or endorsement is claimed. Example records here are completely synthetic.

## Install

Requires Python 3.10+ on macOS or Linux and Codex with local command execution.

```sh
python3 scripts/install.py
```

Or unzip `flat-finder-skill.zip` and copy its `flat-finder` folder to
`~/.codex/skills/`. The installer verifies its manifest, copies only skill files,
and refuses to replace a different existing installation. Open a new Codex chat if
it is not discovered yet. No pip/npm install, API key or social login is bundled.
For a reviewed newer release, `python3 scripts/install.py --update` backs up an
unmodified previous installation. Locally customized skills are left unchanged.

Then tell Codex:

> Use $flat-finder to set up my rental search. I want an entire flat in my preferred
> area, below my rent-plus-maintenance budget, before my move-in deadline. Verify
> my actual commute entrance, search Facebook and rental sites, and show a clickable
> shortlist with costs, source links, availability and walking-route gaps.

For an existing housing project, ask it to read the current requirements and contact
ledger first. Existing explicit permissions and sender ownership remain in force.

## See the product

```sh
python3 flat-finder/scripts/flat_finder.py serve --demo
```

Open **http://127.0.0.1:43126**. The map and six example records demonstrate the
workflow; they are not a live rental feed. The UI includes filters, property details,
source/route links, a research log and Markdown/CSV exports.

For real searches, store `profile.json` and `listings.json` in an external private
directory. Codex can create these using the [data contract](flat-finder/references/data-contract.md).

```sh
python3 flat-finder/scripts/flat_finder.py init --workspace /path/to/private-search --profile /path/to/profile.json
python3 flat-finder/scripts/flat_finder.py serve --workspace /path/to/private-search
```

## What works

- Saved city, housing types, budget, dated deadline, commute anchors and exclusions.
- Strict or inclusive rent-plus-maintenance limits; unknown maintenance stays unknown.
- Radius from verified anchors, with separate exact-entrance walking evidence.
- Current availability distinguished from advertised vacancy dates.
- Canonical-URL merging; protected contacts remain protected across imports.
- Read-only local viewer, responsive map, filters, details, research/access log and exports.
- Source-preserving Codex research workflow, contact checks and truthful delivery states.
- An installable skill and a static, synthetic-only demo package for sharing.

## Boundaries

This is **a skill plus deterministic local tools**, not a Facebook/WhatsApp scraper,
an autonomous background crawler or a live listing service. Codex must actually
inspect sources with available tools. Login, security prompts, history restoration,
provider replies and tool access can require the user. There is no automatic message,
booking, payment, account creation or public posting endpoint. The skill grants no
external action authority; it respects the user's existing explicit permissions.

A populated field is recorded evidence, not independent proof. “Evidence complete”
is not a rental guarantee. No exact walking route is inferred from a radius.
The private viewer is loopback-only; never expose or deploy it with real data.
See [privacy](docs/privacy.md) and [verification](docs/verification.md).

## Share a clean release

```sh
python3 -m unittest discover -s tests
python3 scripts/release.py --check
python3 scripts/release.py
```

Outputs: `dist/flat-finder-codex-1.0.0.zip`, `dist/flat-finder-skill.zip` and
`dist/flat-finder-demo-site.zip`. The site package is built **only** from the bundled
synthetic fixture. It contains no arbitrary private-workspace export option.
`site/` can be hosted as static files after the owner approves the destination.
The release includes SHA-256 manifests. Review [launch drafts](docs/launch-drafts.md)
before posting. The source and synthetic demo links above are published; social launch posts remain drafts.

Map: vendored [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html), BSD-2-Clause,
with recorded npm tarball integrity and file digests. Tiles and attribution follow
the [OpenStreetMap tile policy](https://operations.osmfoundation.org/policies/tiles/).
No tile prefetch or bulk download is implemented. Python helpers use only stdlib.

MIT licensed except the separately licensed Leaflet assets.
