# <img src="src/swingmusic/assets/my_music.svg" alt="" width="32" height="32"> Swing Music with MyAccounts and Workspace

This fork runs as its own music server and Windows **Music.exe**, with the same
player available at Workspace's `/music/` address. Music files stay in the
ordinary `Music` folder inside Workspace's selected files folder. Upload, rename,
move and delete those files in FileBrowser at `/drive/files/My%20Drive/Music`.
The music server scans that folder every 15 seconds when it changes; playlists,
listening history, thumbnails and indexes stay in its separate private data.
All permitted music users share this library. FileBrowser source restrictions
do not automatically become per-track Swing Music permissions.

The current listening preview adds read-only playlist, Liked Songs and library
view sharing with signed-in MyAccounts members. See [sharing and player details](docs/LISTENING.md).
Public Spotify playlist import, existing-song matching and tagged audio downloads
are available from **Import playlist**. See [import and recovery details](docs/SPOTIFY-IMPORT.md).

Workspace installs and supervises the separate executable and registers a
dedicated MyAccounts client automatically. It supplies secrets through the child
environment. The public callback is `/music/auth/myaccounts/callback`; the HTTPS
origin and scheme come from the registered callback, not client-supplied proxy
headers. The Workspace reverse proxy strips `/music` from upstream requests.

## Run independently

For normal local-password standalone use, run `Music.exe --host 127.0.0.1
--port 1970 --config C:\Private\Music`. Set your library folder in the player.
It requires no Workspace or FileBrowser installation.

For standalone **MyAccounts** use, register a confidential authorization-code
client with the exact callback `https://music.example/auth/myaccounts/callback`,
then set these environment variables in a private launcher:

| Variable | Value |
| --- | --- |
| `WORKSPACE_OIDC_ISSUER` | Your MyAccounts issuer |
| `WORKSPACE_OIDC_CLIENT_ID` | The dedicated client ID |
| `WORKSPACE_OIDC_CLIENT_SECRET` | The protected client secret |
| `WORKSPACE_OIDC_REDIRECT_URI` | The exact registered callback |
| `WORKSPACE_MUSIC_DIR` | An absolute path to your Music folder |
| `WORKSPACE_OWNER_SUBJECT` | Exact issuer subject of the intended music administrator |
| `WORKSPACE_BASE_PATH` | Empty for a root-hosted server; `/music` in Workspace |

Keep `--config` on a protected NTFS folder outside shared files. Serve only
through the HTTPS proxy, leaving the process bound to loopback. HTTP is supported
only for localhost/127.0.0.1 development callbacks and issuers. A shared music
folder can be used with standalone FileBrowser by pointing a source at its parent.

MyAccounts mode uses Authlib OIDC discovery/JWKS verification, state, nonce and
PKCE S256. Links use `(issuer, sub)` in a separate SQLite identity table, never
editable email addresses. Normal users receive the user role. Only the explicit
owner subject gets music administration; the first visitor is not made admin.
Local-password creation, guest login and device pairing are disabled in this mode.
JWT cookies are HttpOnly, scoped to the music route, Secure under HTTPS and
bounded by the provider ID token expiry (at most eight hours). Logout remains
app-specific; there is no immediate global session revocation in this preview.

## Build

Use `scripts/build-workspace.ps1` with a Windows Python 3.12 interpreter, uv,
Node/npm and an optional fast build directory. It builds the pinned webclient
v3.0.0 with the small prefix/SSO patch, then creates one `dist/Music.exe` using
`workspace.spec`. Runtime dependencies are in upstream `requirements.txt`, plus
Authlib 1.6.5. PyInstaller and imageio-ffmpeg are build dependencies. FFmpeg 7.1
from imageio-ffmpeg 0.6.0 is bundled for playback/transcoding and is GPLv3; retain
its notices/source links. Swing Music retains AGPLv3; the pinned webclient retains its MIT license.
No premium licensing checks are bypassed. The public-source settings endpoint
handles the absence of optional premium code.

The build now compiles `web/` (React/AUI) and retains the pinned upstream client
as an advanced-settings entry. `scripts/package-client.py` merges assets,
rebuilds compressed copies and omits upstream Apple system fonts. The new UI uses
ordinary system fonts. Additional browser notices are in
[LISTENING-LICENSES.txt](docs/LISTENING-LICENSES.txt). `-Environment` can reuse a
prepared build-only virtual environment. Node/npm/Python are not runtime installs.

The Windows server uses Waitress to avoid frozen multiprocess-server recursion.
Upstream multiprocessing audio parsing retains `freeze_support()` in the launcher.
Build outputs and test credentials stay outside Git. This is an unsigned preview.
