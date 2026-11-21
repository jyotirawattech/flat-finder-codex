# Data and privacy

The public package contains code, documentation and synthetic examples. It does
not contain a user's housing profile, workplace, real property shortlist, phones,
messages, screenshots, credentials or logged-in browser state. The MIT author name
is public attribution, not a login identity.

Store real profile/data files outside the source folder. New files are written
atomically with mode 0600 in a private directory. Use the project's existing shared
writer contract when it is stronger than this helper's local lock. Do not import
raw chat archives; retain short relevant evidence and links in the private project.

The viewer binds only to 127.0.0.1, serves exact assets plus normalized state/exports,
rejects unexpected Host/Origin and cross-site requests, disables caching and has no
mutation or send route. It renders imported text as text, not HTML. This is a local
single-user boundary, not authentication against other local processes or a hostile
browser extension. Do not expose the private server through a tunnel or public host.

The map requests only the tiles in the ordinary viewed area from OpenStreetMap.
This discloses the viewed geographic tile area and standard request metadata to
the tile provider. Listing text, contact details and private profile JSON are not
sent to it by the application. No analytics, tracking scripts or API keys are used.
Source links open their respective providers. Normal provider sign-in/security and
privacy rules still apply when Codex researches those sites.

Release builds accept no private workspace path and always compile the bundled
synthetic fixture. The release scanner checks for common accidental private markers,
source/example invariants, vendor integrity and the skill manifest. This is a useful
guardrail, not a guarantee that a later contributor cannot add sensitive content.
Review the exact archive before publishing it. A local build is not a public release.
