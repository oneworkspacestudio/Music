# Spotify audio matching follow-up

User reports failed download; prior authorization covers push, new release and
normal backed-up installation on both PCs. Base de8916e3 (public Music2), isolated
codex/music-import-search-fix. Use a new immutable Music3 release; do not alter2.
Engine/client compatibility remains3.0.1; identical merged UI reused from tested2.

Reproduced unquoted search silently returning unrelated songs for a rare title;
quoted title+primary artist finds its official Topic upload. Original match
failure inherits ValueError and was swallowed as a JSON failure. Separate parsing
and matching; exact query first, bounded broader fallback; recognize distributor
Topic/VEVO, official presentation labels and credited artist/ft markers while
retaining version and duration checks. Cancellation and explicit resume preserved.

Seven Python tests pass (31 existing warnings), including captured public result
shape, short-title and featured-credit matches, fallback, wrong versions/duration/
artists, malformed responses, cancellation and existing owner/resume/index tests.
Reported recording downloaded into named synthetic task scratch as valid tagged
MP3,172.464s vs173s expected. No owner identities/library used as fixtures.

Artifacts I:/Projects/tooling/music-spotify-match-20261024; NTFS scratch only
C:/Projects/.cache/music-spotify-match-20261024. Final build/native checks,
publication, channel and both deployments pending. Actual secondary owner has a
running separate import; wait for completion before updating. Do not stop its job
or use owner libraries as test fixtures. Other app releases proceed concurrently;
preserve current full channel, select only Music and retain manager80.

## Release/install checkpoint

Immutable Music3 published at d6d28d52, exact native-tested/public-downloaded
SHA2563fb3dd88401e3b70ac51b2edbf54470706c8a8bb29e84de394d3c91e5dfb5255.
All20 public asset sizes/digests verified. Both native OIDC/player/share/import/
phone and standalone checks pass. Full index promotion62a62ec retains all previous
records including concurrent MyAI/Workspace81. Default raw URL with normal updater
request headers and real credential-free Music-only selection verified. Python's
default headers briefly served a stale CDN variant; normal updater headers saw3.

Both normal backed-up updates2 ->3 accepted once around16:33UTC. Main
ApplyMusic3.exe process logs installation-local.log, receipt installation-local.json
at task artifact root. Normal backup copies4.476GB; do not replay. Secondary Chrome
tab585734103 (fixUpdates) selected only Music and reached backup/service shutdown,
now automatic reconnect. Before versions in CUA beforeMusicFix. Preserve managers80
and other apps. Owner's27-track import completed before update:21 ready,6 failed;
do not automatically retry that separate job. After updates, resume only the
reported failed single-track import via Afrobeats2025 recent entry and verify ready.
No owner jobs used as fixtures. Browser handles songFixPage585734104 and
localSongFixPage585734105 show Music. Save final sanitized receipts and UI proof.

All own test services stopped; named C scratch removed after verifying ten pytest
links stayed within it. Temporary harness files removed from prior worktrees.
Delivery verification, actual reported-import resume and docs-only push remain.

## Delivered

Both normal protected Music2 ->3 updates completed, retaining Workspace80.
Main exact binary, manager, unselected app/package contracts, owner settings and
decrypted identities/credentials verified; all25 services running, transaction
complete, exact unchanged UI/SW identity+gzip served and newest recovery retained.
Standard cleanup removed one older backup (~4424MB), preserving items needing
review. Secondary UI completed in12m24s, all apps healthy, newest recovery kept;
fresh release check changes only Music to3. Remote digest validated by normal
updater; no manual remote hashing claimed. Other active owner import finished
before update and was not retried or used as a fixture.

Resumed the original reported single-track failed import through actual secondary
Music UI. It now shows Complete,1 ready/1 checked, Downloaded and Added to your
library. Original playlist remains present; library grew by one. This was the
requested recovery action after synthetic/network verification, not a test fixture.
Its result tab remains open. Do not auto-resume unrelated partial jobs.

Sanitized evidence in docs/evidence/spotify-match-*20261024.json. Screenshot
capture in the real Chrome session repeatedly timed out (including a fresh tab);
no screenshot claimed or substituted. Actual DOM/AX result and both installation
receipts verified. Source tag remains immutable d6d28d52; delivery documentation
does not rebuild or retag. No required implementation/release/install steps remain.
