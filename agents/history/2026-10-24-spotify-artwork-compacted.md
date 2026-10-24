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

## Published/installing

Immutable4 published from6124da1d, final SHA25628e567a89dec5bcaab7db1edc443ff1405f1b2163384d4ad31b29ecec4064e41.
All20 assets verified; public downloaded executable matches. Exact native checks
also import real public playlist art in synthetic account, Refresh artwork keeps
it, image loads on phone/desktop; bundled yt-dlp/Node and ffmpeg.exe execute.
Initial private candidate staged FFmpeg under vendor filename; caught before
publication, rebuilt correctly and added spec/runtime-check guards. Final source,
UI and embedded ZIP verified; no incorrect candidate published.

Full index75005b6 preserves concurrent updates/withholding, default raw normal
headers and real unauthenticated selection verified. Concurrent authorized MyAI
task installed main Workspace82 before our update; preserve82/MyAI2. Recompiled
ApplyMusic4 against current82 suite using patched official Go1.27.3 module runtime.
Old80 helper is not used. Main accepted normal Music3 ->4 update, logging
installation-local.log at artifact root (receipt installation-local.json pending).
Secondary remains manager80; Chrome artRemoteUpdates tab585734109 selected ONLY
Music (explicitly unchecked Workspace82 and MyAI2), accepted one update request.
Before versions in CUA artRemoteBefore. Do not replay either request.

Secondary artRemoteMusic tab585734110 has Dance partial import, no active song
download. After completion reload, select Dance recent entry if needed, click
Refresh artwork (not Resume), Open playlist, verify .collection-hero .cover img
has /img/playlist/thumb_spotify- URL and naturalWidth>0, same songs/playlist.
Actual owner recovery is authorized; never use owner identities/library as fixture.
Main/secondary installed UI/evidence and final docs push remain. C scratch already
removed after all fixtures stopped and21 pytest symlinks checked/unlinked.

Main normal update complete: retained Workspace82/MyAI2 and all unselected app/
package contracts, owner settings and decrypted credentials; exact tested Music4
digest installed, all26 services running, new JS/CSS and SW identity+gzip verified,
transaction complete and newest recovery kept. Normal cleanup removed one older
copy (~4482MB), preserving items needing review. verified-local.json saved.

Secondary installed/startup checks passed, now normal cleanup verifies older
retained copy (16m elapsed). Do not replay. Actual updated Music Refresh artwork
on the existing Dance job returned Playlist artwork imported. Compared full
rendered import-track results before/after: unchanged. Opened original playlist;
private /img/playlist/thumb_spotify-* cover loads250x250 and20 song rows remain.
No song download/reimport ran. Actual-artwork-verification.json is sanitized;
screen capture again timed out, no actual screenshot claimed. Result tab110 and
main111 marked deliverables. Secondary completion receipt/version comparison and
final docs pushes remain. Do not publish real owner capture/private playlist data.

## Delivered

Secondary normal update completed18m41s, all apps healthy, newest recovery kept;
one older copy removed (~3561MB). Fresh check changes only Music3 ->4 among prior
apps, retains manager80 and leaves unrelated MyAI uninstalled. Main retained82/
MyAI2 as above. verified-remote.json and actual artwork repair proof copied into
docs/evidence/spotify-artwork-*20261024.json alongside build/native/browser/network/
publication/channel/local/cleanup receipts. No actual owner screenshot available:
Chrome capture timed out; DOM image dimensions/load and song-state checks passed.
Real playlist result remains open. No required implementation, release, channel,
installation, repair or scratch cleanup remains. Final docs-only commit does not
move immutable4 tag6124da1d or rebuild its verified executable.
