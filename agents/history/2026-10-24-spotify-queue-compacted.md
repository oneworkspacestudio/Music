# Durable Spotify import queue

User requests playlists queue instead of rejecting concurrent imports, and resume
automatically. Prior push/release/install both PCs authorization continues. Base
066f3e98 Music4; isolated codex/music-import-queue. Target immutable Music5,
engine/client compatibility3.0.1 unchanged. No agents or Actions; no owner fixtures.

ImportManager saves FIFO acceptance order, reserves one worker under its lock,
advances after completion/failure/cancel, and restores accepted queued/running or
legacy interrupted work after migrations and library stores load. Browser need not
reconnect. A separate persisted stop_requested column survives stale progress
writes and process loss: explicit stops stay paused; previews/completed/failed jobs
are not automatically accepted or retried. Resume keeps playlist identity and
successful songs. Every worker rechecks principal/random playlist identity before
artwork/downloads. Deleted/reused accounts or playlists cancel without blocking the
next job. All active jobs survive recent-history pruning and listing limits.

AUI queue positions/remove/resume controls, restart explanation and persistent
history polling while another preview is selected. Compiler source retained;
controller guards in-flight mutation/poll races and restores original mode on resume.
16 Python tests pass (31 existing warnings), including concurrent duplicate starts,
FIFO by acceptance, queued/running cancellation, durable stop vs stale writes,
legacy recovery, deleted/reused identity and history retention. Synthetic browser
1440/390px passes three-job progression, live history, queued remove/resume,
reload, no overflow, actual original generated MP3 index/play and cover handling.
Exact Windows binary passes signed OIDC/play/share/lyrics/classic settings/artwork,
bundled tools and fresh standalone checks. Native crash-checkpoint restart resumes
accepted work before any browser reconnects, preserves stopped jobs and previews.

Final executable SHA256
73f40020544def64521f3bc8d9d04b88c31ffb9dc8abc25c18fb9c5f0ab2a531.
Application stage, reviewed UI and embedded merged ZIP bytes verified. Official
FFmpeg7.1 is staged as ffmpeg.exe; pinned yt-dlp/Node hashes execute. Art CDN network
checks pass. Defender real-time enabled, no task-path detections; no completed
custom scan claimed. Unsigned preview; no physical-phone/clean-host/reboot test.

Artifacts I:/Projects/tooling/music-spotify-queue-20261024, only disposable NTFS
root C:/Projects/.cache/music-spotify-queue-20261024. Publication/channel and both
normal backed-up Music-only installs next. Main currently Workspace82/Music4/MyAI2;
secondary known80/Music4, currently tunnel1033 then502 on Music and Updates.
Retain all unselected apps/settings/credentials and newest usable recovery. Honor
channel withholding81/MyAI1 and concurrent main changes. Use patched Go1.27.3
helper against current suite sources. After deployment verify actual queue UI;
recover only accepted work or the explicitly requested blocked Happy Mix preview.
Do not silently resume all old partial imports. Stop fixtures, inspect links/process
references then remove named C scratch and retain sanitized receipts. Immutable tag
must stay on functional source; final delivery docs do not rebuild or retag.
