# My Music listening preview

The new interface follows the supplied desktop and phone layout references:
library/main/now-playing panels and a fixed desktop transport, with artwork
headers, compact song rows, a mini-player and bottom navigation on phones.
My Music keeps its own identity and uses the server's actual songs, cover art,
metadata, local lyrics and listening history. It does not provide Spotify's
catalogue, accounts, recommendations, podcast service or playback synchronization.

Create playlists from **Create**, add songs, edit the name and description,
and use each song's options menu for queue, playlist and album actions.
Search covers indexed titles, artists and albums. The player supports seeking,
shuffle, repeat, volume and browser media-session controls. Album/artist and
search lists load more results in batches. Advanced library, indexing, plugin
and standalone preferences remain available through **Settings**.

## Share collections

Open a playlist, Liked Songs or Song library and choose **Share**. Select members
and save. They receive a collection under **Shared with you**. Recipients may
view and play only; only the owner can edit, grant or revoke access. Copying a
link does not grant permission. Clear a member's selection and save to revoke.
Open shared pages recheck access every 15 seconds and on reopening.

The member picker includes users who have signed in to this My Music server.
In MyAccounts mode they must belong to the same verified issuer as the sharer.
Identities and grants are bound to signed issuer/subject, not mutable email, name or reusable local database IDs. Standalone users have a random account identity. Replacing a deleted account cannot inherit its grants or like overrides.
Members who have never opened My Music should sign in once before being selected.

The existing server Music folder is already available to permitted music users.
Sharing adds a curated collection view; it does not introduce per-file isolation
or revoke somebody's existing access to that common folder. **Song library** is
the current indexed server collection; **Liked Songs** is the owner's saved list.
Shared playlists and libraries reflect later edits. Listening history and likes
remain personal. No public anonymous share links or collaborative editing exist.

## Storage and compatibility

Native playlist IDs and upstream data stay intact. Grants and personal like
overrides live in private `music-sharing.sqlite3` next to the existing Music DB.
Existing favourites are read through; no destructive conversion is required.
Existing standalone sessions may need one new sign-in after the identity upgrade.
The normal Workspace backup includes the new database. Runtime remains a portable
Windows executable with its Python engine, browser assets and FFmpeg embedded.

Packaged UI versions are checked against the bundled version. A mismatch stops
startup with a reinstall instruction; frozen builds never download a different
upstream interface. The previous service worker's cached HTML is retired.
The classic settings entry uses the same authenticated route and API bindings.
Source/build dependencies and notices are in the repository and release assets.

## Verification

Tests use disposable NTFS stores and synthetic audio/artwork only. They cover
real SQLite/JWT ownership and CSRF checks, issuer boundaries, revocation, separate
likes, signed OIDC state/nonce/PKCE/audience checks, bundled-version handling,
browser playback and seeking, responsive layouts and server persistence.
`web/scripts/native-acceptance.mjs` additionally launches the Windows executable
against a disposable RSA-signed OIDC provider and a real tagged MP3. Its receipt
records exactly which checks passed against the released digest.

No physical-phone, clean-host, reboot, code-signing or synchronized-listening
claim is made. On this build host Defender real-time protection is enabled;
on-demand custom scans currently return errors. The earlier quarantined build
remains withheld and is never reused. Release evidence distinguishes those
conditions from a completed malware scan.
