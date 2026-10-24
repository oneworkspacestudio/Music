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
