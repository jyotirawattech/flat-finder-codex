# Verification

Version 1.0.0 is a local Codex workflow with a [published synthetic demo](https://flat-finder-codex.pages.dev) and [public release](https://github.com/jyotirawattech/flat-finder-codex/releases/tag/v1.0.0). Verification
covers the deterministic helpers and viewer behavior; it does not establish real
provider availability, recipient identity, message delivery or rental success.

Run:

```sh
python3 -m unittest discover -s tests -v
node --check flat-finder/assets/viewer/app.js
python3 scripts/release.py
python3 scripts/release.py --check
```

The tests exercise strict/inclusive budget limits; unknown maintenance; actual
radius versus walking evidence; fresh and stale source/route/availability evidence;
explicit deadlines and timezone; verified and room-specific anchors; held/closed/
sent/unknown suppression; canonical-source and cross-source phone deduplication;
invalid URL/numeric values; atomic failure behavior; private file permissions; CSV
formula escaping; read-only endpoints, traversal, Host/Origin and asset MIME types.

Browser acceptance includes desktop/mobile layout, home-type/status/search filters,
property details, protected conversation state, research log, exports, static demo
fallback and available source/map links. The demo does not contact providers.

The installation is checked against the skill manifest. The release validates
Leaflet's pinned vendor hashes and synthetic-only data, then adds SHA-256 manifests
to the ZIPs. Tests are not a comprehensive penetration test or third-party audit.

No live accounts, credentials, deployment, public posts, visits or payments are
part of these checks. Existing housing access requests and operations remain in
the separate private project, with their original owners and receipts.

Production readback on 21 November 2026 confirmed the demo HTML, JSON, JavaScript,
CSV and downloadable skill match the reviewed build. The live site sends CSP,
nosniff and referrer headers. A browser skill download matched the release SHA-256.
Pages was deployed through the signed-in dashboard Direct Upload workflow; the CLI
OAuth callback did not complete. No private profile or housing records were hosted.
