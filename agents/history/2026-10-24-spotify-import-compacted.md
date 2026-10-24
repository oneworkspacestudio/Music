# Spotify playlist import and download

User authorizes feature implementation, source push, release and installation on
both workspace.m8e.co.uk and workspace-2.m8e.co.uk. Preserve listening UI and
MyAccounts view/play sharing. Base2f6b735d on public Music/master; isolated source
I:/Projects/tooling/music-spotify-20261024/source, branch codex/music-spotify-import.
Do not modify previous Music or Workspace worktrees or reuse quarantined binaries.
No agents or Actions.

spotify_import.py reads bounded public Spotify embed metadata (no API keys),
previews its returned snapshot, matches existing songs, queues per-account jobs,
downloads duration/title/artist-matched YouTube audio through pinned official
yt-dlp2026.10.21/Node26.8.2 plus existing FFmpeg, writes MP3 ID3 tags and optional
Spotify album/year/art. Private/omitted entries and public snapshot limits are
explicit. No Spotify audio extraction, credentials, cookies or DRM workarounds.

Jobs bind stable principals and random playlist identities, inherit JWT/Origin/
CSRF rules, retain work on cancel/restart and only resume explicitly. Repeated
start does not duplicate playlists. Other accounts cannot access jobs. One active
worker; fixed tool arguments, no shell, bounded outputs/timeouts, child termination
on cancellation; Workspace/publisher environment secrets stripped. No original
file overwrite. SQLite playlist append preserves concurrent owner edits. Download
files live under the configured Music folder; job DB stays private.

React controller with generated Imports.aui screen, desktop header and phone
Library/Settings entries. Preview, toggle missing-song downloads, progress/results,
cancel/resume, recent imports and Open playlist; refresh restores ongoing state.

Real import indexing exercised old watcher code and exposed an unavailable type
alias, inverted empty-colour handling, missing Track constructor fields and duplicate
filepath insertion. Updated type to BaseObserver, cached/empty colour handling,
construct from complete DB row/config, SQLite filepath upsert preserving play stats,
and normalized paths. Actual generated MP3 indexing/playback and repeated indexing
now pass. Do not discard these fixes when rebuilding the candidate.

Verification so far: five Python tests pass (31 existing deprecation warnings),
UI build passes. Synthetic browser desktop1440x940/phone390x844 passes invalid URL,
preview/existing reuse, cancellation/resume same playlist, generated audio download/
index/playback, phone Library entry, reload persistence, no overflow/page errors.
Public Spotify returns50 tracks; actual YouTube Audio Library Spring In My Step
download passes MP3 duration/title/artist tags. No owner identities/media as test
fixtures. Initial test-environment missing installed metadata/mutagen corrected;
mutagen1.48.1 added to pinned requirements. Fixture readiness uses onboarding-data.

Candidate Windows build finished before final watcher/target validation changes:
must rebuild final executable from final source and run native checks before
publication. App version3.0.1-workspace.2; engine/client compatibility3.0.1 unchanged.
Build tools and evidence durable I:/Projects/tooling/music-spotify-20261024.
Only disposable C scratch C:/Projects/.cache/music-spotify-20261024. Stop all tracked
fixtures, save receipts and remove scratch with exact path/reparse checks at end.
C free space dropped below1GB due other work while this task owns about1GB; inspect
current space/normal updater preflight before any installation. Do not delete
unrelated caches, owner libraries, private keys or recovery archives. Publication,
channel promotion, both installations and final delivery record remain pending.

Final application stage and merged client bytes verified against source. Rebuilt
Windows binary b1831b5f9550db1cfef362f19d8173ef95c76a975e464f5ca1b785f356ab4487
passes full native signed-OIDC/player/share/revoke/lyrics/classic settings checks,
public Spotify preview on desktop/phone, bundled downloader+Node exact hashes and
execution. Standalone creation/index/play/login/logout also passes. Six Python
tests now include repeatable immediate indexing preserving playback statistics.
Source handling retains Unicode titles/artists so unrelated non-Latin names do
not collapse to an empty match. Defender real-time enabled, no task-path detections;
no completed custom scan claimed. Source/evidence commit and release publication
follow. C free space recovered to roughly7GB while other work completed; recheck
against the normal conservative backup requirement after our cache cleanup.


## Publication and installation checkpoint

Immutable v3.0.1-workspace.2 published fromb27a079203f36239779accb1637c85bd00da878c;
all20 public asset sizes/SHA256 match. Public downloaded Music.exe matchesb1831b5f.
Channel promotion20a878c in Workspace main; default raw index and real credential-free
Music-only SelectUpdates verified. New notice terms aggregate into existing registered
SwingMusic-LICENSE path, with individual full notices/source assets also released;
no new manager package ownership rules needed. Do not retag/rebuild/replace assets.

Main manager80/Music1 selected only Music2 using ApplyMusic2.exe normal suite updater.
Protected preflight passed after space recovered/own build scratch cleanup. Main
4.418GB snapshot copying; owner settings/identity and unselected contract checks occur
after completion. installation-local.log/json track this operation. Do not replay.
Remote manager80/Music1 fresh Chrome Updates selected only music, accepted one request
and downloaded Music2. Now tunnel paused for backup/restart; preserve live tab585734099
(remoteMusic2 in CUA). Before snapshot remoteBeforeMusic2 contains only public app
version metadata; compare after completion. Do not replay its install POST.

Original build/fixture scratch was removed after native checks. A small fresh
C:/Projects/.cache/music-spotify-20261024/final-check environment is now running six
final source tests (including the added Unicode case) during backup waiting time;
save final-source-tests.log and remove this recreated scratch after its process exits.
Base Python for remaining standard-library publisher/verification scripts is
C:/Users/fahim/AppData/Local/Programs/Python/Python312/python.exe. All release artifacts,
final merged client ZIP and executable are durable under I task directory.

## Delivery complete

Both PCs completed normal protected Music-only updates1 ->2, retaining Workspace80.
Main receipt verifies exact tested binary, manager, unselected app/package contracts,
owner configuration and decrypted identity/credentials. Transaction complete,
all25 local services running, actual JS/CSS and identity/gzip service-worker bytes
match the tested build, latest recovery copy retained. Standard cleanup removed
one older automatic backup (~4420MB) and kept older items needing review; no manual
owner/recovery deletion. Main owner browser displays the new import screen normally.

Remote normal UI reports Update complete, all apps healthy, cleanup removed one
older copy (~3395MB), newest recovery retained; completed in12m12s. Fresh release
check confirms Music2 and before/after comparison changes only Music, retaining
manager80 and other visible app versions. Existing owner session opens new import
screen without a new account or private fixture. Remote executable was validated
by the normal updater, not manually hashed from this PC.

Actual secondary installed UI screenshot is privacy-safe (empty library/form),
docs/screenshots/spotify-import-installed-remote.png. Main DOM/AX and exact served
assets were verified; Chrome capture of that background tab repeatedly timed out,
so do not claim a successful main screenshot. Both live Music import tabs are kept
as deliverables. No real owner playlist preview/download was used as a fixture.

Fresh final source environment also passes all6 tests/31 existing warnings,
including Unicode matching and repeatable indexing. Setup initially omitted
explicit build-script Authlib/SCM dependencies; installed them and reran successfully.
Final test processes stopped. Recreated named C scratch removed after verifying and
unlinking ten pytest-current symbolic links entirely within that exact scratch;
no links followed or unrelated/global caches removed. Final cleanup receipt saved.

Sanitized publication, both installation and cleanup receipts are in docs/evidence/
spotify-*20261024.json. All release artifacts remain immutable at sourceb27a0792;
final documentation-only commit does not move its tag or rebuild payloads. No
remaining implementation, publication or deployment work for this request.
