# Spotify artwork follow-up

User reports missing imported playlist image; prior push/release/install-both
authorization continues. Isolated codex/music-spotify-artwork from public4d626882
(Music3). New immutable release4; engine/client compatibility3.0.1 unchanged.

Root causes: playlist creation always image=None and no cover fetch; track metadata
uses visualIdentity.image and Spotify image CDN hosts, not only coverArt.sources.
Select highest supported public image, validate exact fixed HTTPS CDN/path, bound
response/pixels, decode JPEG/PNG/WebP, normalize private WebP+thumbnail. Import
worker copies cover optionally; audio survives absent art. Track downloads embed
visualIdentity artwork and parse releaseDate.isoString. Existing imports gain
owner/CSRF-protected Refresh artwork action via Imports.aui compiler. Repair keeps
playlist/song state and existing custom covers, rechecks principal+random playlist
identity after network read, serializes DB updates and never overwrites files.
No automatic startup migration/network requests or existing MP3 rewriting.

Nine Python tests pass (31 existing warnings): CDN/invalid-response/dimension
handling, actual generated MP3 APIC/year tags, real SQLite legacy repair, owner/
CSRF denial, preserving songs and existing covers, existing import/resume/matching/
identity tests. Synthetic browser phone390/desktop1440 passes import/cancel/resume,
private cover rendering and Refresh artwork, real generated MP3 index/play, reload
and no overflow. Public playlist and track artwork fetch/decode pass current CDN.
No live owner identities/library as fixtures, agents or Actions.

Artifacts I:/Projects/tooling/music-spotify-art-20261024; only disposable NTFS root
C:/Projects/.cache/music-spotify-art-20261024. I npm dependency extraction was slow;
stopped its exact task-owned tree and built UI on named NTFS root. Classic client
reconstructed from verified previous merged ZIP, new listening build merged with
deterministic gzip. Native build and checks underway. After exact final checks:
source push/new release4, refresh full current public channel (honor withheld
releases/concurrent work), normal Music-only backed-up install both PCs (currently
manager80/Music3), then use actual secondary Dance import Refresh artwork and
verify real cover loads. Do not resume unrelated song downloads. Clean task
fixtures/scratch after receipts; retain owner data and newest recovery backups.
