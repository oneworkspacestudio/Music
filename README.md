<p align="center">
  <img src="src/swingmusic/assets/my_music.svg" alt="My Music logo" width="112" height="112">
</p>

<h1 align="center">My Music</h1>

Your own music library, powered by Swing Music. Run a standalone player or connect it to One Workspace for MyAccounts sign-in and a shared Music folder visible in Drive.

[Download Windows preview](https://github.com/oneworkspacestudio/Music/releases) · [Standalone and suite setup](WORKSPACE.md) · [One Workspace](https://github.com/oneworkspacestudio/one-workspace) · [Upstream Swing Music](https://github.com/swingmx/swingmusic)

![My Music desktop player with a playlist, library and now-playing panel](docs/screenshots/listening-desktop.png)

[Phone layout](docs/screenshots/listening-phone.png) · [Playback and sharing guide](docs/LISTENING.md)

## Listen your way

- Browse albums, artists and playlists in a three-panel desktop player or a phone layout with a mini-player and bottom navigation.
- Play, seek, queue, shuffle and repeat your indexed music; read local lyrics and return to recent listening.
- Share playlists, Liked Songs or your song-library view with MyAccounts members. Recipients can view and play; owners can revoke access.
- Run the portable Windows server independently with normal local-password sign-in.
- Use MyAccounts for the connected suite, with ordinary user roles and a specifically assigned owner.
- Upload music through Drive and play the original files; the library is not copied into a second media store.
- Keep listening data, indexes and player metadata in Music's separate private-data folder.

## Install with One Workspace

Use the [Workspace installer](https://github.com/oneworkspacestudio/one-workspace/releases). The suite registers the Music OIDC client, creates the shared `Music` folder and opens the player at `/music/`.

Changes to the shared Music folder are rescanned about every 15 seconds. All permitted Music users share that library; Drive folder scopes do not become per-track Music permissions automatically. See the [storage and identity details](WORKSPACE.md).

## Run independently

Download `Music.exe` from this fork's [Windows preview](https://github.com/oneworkspacestudio/Music/releases), then start it with a private configuration folder:

```powershell
.\Music.exe --host 127.0.0.1 --port 1970 --config 'D:\Private\MyMusic'
```

Open `http://localhost:1970`, create your local account and choose your library. Standalone use does not require Workspace or FileBrowser.

For shared sign-in, register a dedicated MyAccounts OIDC client and configure the protected environment described in [WORKSPACE.md](WORKSPACE.md). MyAccounts mode disables local/guest account creation and device pairing; use the browser login for the integrated preview.

## Build locally

```powershell
./scripts/build-workspace.ps1 -Python 'python' -BuildRoot 'I:/Build/MyMusic'
```

The Windows package combines the Python server, React/AUI listening client and pinned webclient v3.0.0 for advanced settings, with the base-path/SSO adapter and My Music artwork. The script uses Python 3.12, uv, Node/npm and PyInstaller; it produces `dist/Music.exe`. Builds run locally without GitHub Actions.

The server uses Waitress on Windows. See [build/runtime notes](WORKSPACE.md) for dependency versions, FFmpeg provenance and standalone settings. Upstream deployment documentation and Docker examples are retained in the [earlier README](docs/README-archive.md).

## Preview status and licenses

The Windows integration is an unsigned preview. App sign-out is local to Music; immediate global session revocation is not implemented in this preview.

Swing Music retains the [AGPLv3 license](LICENSE), the pinned webclient retains its MIT license, the listening client dependencies have [bundled notices](docs/LISTENING-LICENSES.txt), and bundled FFmpeg has its own GPL terms and source requirements. Optional premium features remain subject to upstream licensing. Credits, contributors and upstream community links are preserved in the [archived README](docs/README-archive.md).
