# My Music listening layout and read-only sharing

User requests desktop/phone layout matching the supplied Spotify references,
playlist and song-library sharing with MyAccounts members, source push, release,
and local installation. Recipients confirmed view/play only. My Music keeps its
own brand, actual indexed songs and original/synthetic test art. No agents or
Actions used. Base b00d423f; branch codex/music-listening-sharing.

React/AUI shell under web/ supplies library/main/now-playing desktop columns,
artwork headers/song lists, phone mini-player/bottom nav, playback/seek/queue,
shuffle/repeat/volume/media session, lyrics, albums/artists/search, personal likes
and history, playlist CRUD and sharing. Large play buttons toggle pause; closing
Add songs during its async request cannot reopen the dialog. Settings links
source and retained authenticated classic Vue advanced settings (?classic=1).
Classic settings category titles and hash history query handling are fixed.

/studio API uses signed JWT identity, Origin and principal-bound HMAC CSRF.
Private music-sharing.sqlite3 grants/like overrides use stable signed issuer/sub
hashes or random local-account identities, not reusable SQLite IDs or email.
Playlist grants also bind a random per-playlist identity. Existing playlists and
local users receive identities at startup; old local sessions need one sign-in.
Recipients must have opened Music and share the owner's issuer. Collection
readers cannot edit/delete/reshare; revoke rechecks each request. Native classic
playlist deletion now checks ownership; classic saved-song removal is scoped.
Existing favorites read through SQL rather than stale in-memory fav_userids.
Native playlist IDs and common media folder semantics remain intact. Collection
sharing does not introduce per-file access isolation. No public anonymous links.

Package engine/UI3.0.1; app version3.0.1-workspace.1, tag v3.0.1-workspace.1.
Frozen engine version uses bundled version.txt, rejects mismatched bundled UI
before removal/download. run.py always extracts verified embedded client.zip to
its private runtime temp. Merged UI preserves classic settings, rebuilds gzip
and retires old caching SW; upstream Apple fonts excluded. Pinned webclient ZIP
SHA75a3dbfd5a3c3f52ab10046197e9766ff370adbb369e3e35a14a434cf0e5d7b9.

Verification: 3 comprehensive SQLite/JWT, signed OIDC and package-version tests
pass;31 existing deprecation warnings. Browser1912x941/390x844/768x1024 passes
playback/seek/share/revoke/lyrics/persistence/no overflow or page errors. Exact
Windows executable passes standalone create/login/index/playback and three real
RSA-signed OIDC sessions, native MP3 index/play/seek/pause/scrobble, read-only
sharing, legacy API denial, revoke, lyrics and classic settings. Receipts and
exact digest in docs/evidence/listening-20261023.json. Synthetic disposable data
only; no live owner identities/media used as fixtures. No physical phone,
clean-host, reboot or signing claim. Defender real-time enabled, no task-path
detections; host custom scans errored (MpCmdRun0x80508023), never claim completed
scan. Older Oct15 quarantined build remains withheld; do not reuse or restore.

Artifacts I:/Projects/tooling/music-listening-20261023; disposable NTFS scratch
C:/Projects/.cache/music-listening-20261023. I: Python imports stalled; C runtime
resolved it. Do not build/run old repo dist/Music.exe. Final tested build is C
scratch/source/dist/Music.exe, soon copied to durable release/Music.exe. Never
change protection. Test processes must stop before bounded named-cache cleanup.
Preserve owner C:/tmp/workspace and all recovery archives/private keys.

Publication/install pending at this source commit. Installed manager changed
concurrently from74 to75; exact published75 source/catalog downloaded and hash
verified outside other chats' worktrees. ApplyMusic75 helper uses normal backed-up
Music-only update, verifies unchanged manager/other app contracts/settings and
secrets, and clears publisher token before any runtime preflight launch. Recheck
installed version and transaction immediately before update. Promote public
updates/releases-v1.json after publication from isolated channel-source checkout;
verify raw public tag and unauthenticated selection. Do not move immutable tags.
