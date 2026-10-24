"""Account-owned Spotify playlist imports and bounded public-audio downloads.

Spotify supplies metadata only. No Spotify credentials, stream extraction,
browser cookies, arbitrary download URLs or shell commands are accepted.
"""
from contextlib import contextmanager
import difflib
import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import requests
from flask import Blueprint, abort, current_app
from sqlalchemy import select, update

MAX_TRACKS = 1000
ACTIVE = {"queued", "running"}
TERMINAL = {"complete", "partial", "cancelled", "interrupted", "failed"}


class ImportProblem(ValueError):
    pass


class ImportCancelled(Exception):
    pass


def playlist_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        raise ImportProblem("Paste a Spotify playlist link.")
    value = value.strip()
    if re.fullmatch(r"spotify:playlist:[A-Za-z0-9]{22}", value):
        return "https://open.spotify.com/playlist/" + value.rsplit(":", 1)[1]
    try:
        p = urlsplit(value)
    except ValueError:
        raise ImportProblem("Use an https://open.spotify.com/playlist/… link.") from None
    match = re.fullmatch(r"/(?:intl-[a-z]{2}/)?(?:embed/)?playlist/([A-Za-z0-9]{22})/?", p.path)
    if p.scheme != "https" or p.netloc != "open.spotify.com" or not match or p.fragment:
        raise ImportProblem("Use an https://open.spotify.com/playlist/… link.")
    return "https://open.spotify.com/playlist/" + match[1]


def public_bytes(url, limit=3_000_000):
    # All callers construct the URL or validate the fixed public CDN host.
    with requests.get(url, timeout=(8, 20), allow_redirects=False, stream=True,
                      headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "en"}) as response:
        if response.status_code != 200:
            raise ImportProblem("Spotify could not share this playlist. Check that it is public and try again.")
        content = bytearray()
        for chunk in response.iter_content(32768):
            content.extend(chunk)
            if len(content) > limit:
                raise ImportProblem("The playlist response was too large. Try a smaller playlist.")
        return bytes(content)


def entity_from_html(page):
    match = re.search(r'<script\b[^>]*\bid=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ImportProblem("Spotify did not provide a readable track list. Try again later.")
    try:
        entity = json.loads(match[1])["props"]["pageProps"]["state"]["data"]["entity"]
    except (ValueError, KeyError, TypeError):
        raise ImportProblem("Spotify did not provide a readable track list. Try again later.") from None
    if not isinstance(entity, dict):
        raise ImportProblem("Spotify did not provide a readable track list.")
    return entity


def artwork_url(entity):
    sources = []
    for key, field in (("coverArt", "sources"), ("visualIdentity", "image")):
        value = entity.get(key)
        rows = value.get(field) if isinstance(value, dict) else None
        if isinstance(rows, list):
            sources.extend(row for row in rows if isinstance(row, dict))
    sources.sort(key=lambda row: next((n for n in (row.get("height"), row.get("maxHeight")) if type(n) in (int, float)), 0), reverse=True)
    return next((row["url"] for row in sources if valid_artwork_url(row.get("url"))), None)


def valid_artwork_url(value):
    if not isinstance(value, str) or len(value) > 2048:
        return False
    try:
        p = urlsplit(value)
    except ValueError:
        return False
    hosts = {"i.scdn.co", "image-cdn-fa.spotifycdn.com", "image-cdn-ak.spotifycdn.com"}
    path = r"/image/[a-fA-F0-9]{20,200}"
    if p.netloc == "mosaic.scdn.co":
        path = r"/[0-9]{2,4}/[a-fA-F0-9]{20,1000}"
    elif p.netloc not in hosts:
        return False
    return p.scheme == "https" and not p.query and not p.fragment and bool(re.fullmatch(path, p.path))


def artwork_image(url):
    import io
    from PIL import Image
    if not valid_artwork_url(url):
        raise ImportProblem("Spotify did not provide supported artwork. Try refreshing artwork later.")
    raw = public_bytes(url, 2_000_000)
    try:
        with Image.open(io.BytesIO(raw)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP") or image.width * image.height > 10_000_000:
                raise ImportProblem("Spotify artwork could not be read safely.")
            image.thumbnail((800, 800))
            return image.convert("RGB")
    except (OSError, Image.DecompressionBombError) as error:
        raise ImportProblem("Spotify artwork could not be read. Try refreshing artwork later.") from error


def resolve_playlist(value):
    source = playlist_url(value)
    try:
        entity = entity_from_html(public_bytes(source.replace("/playlist/", "/embed/playlist/")).decode("utf-8"))
    except requests.RequestException:
        raise ImportProblem("Could not reach Spotify. Check the server connection and try again.") from None
    rows = entity.get("trackList")
    if not isinstance(rows, list) or not rows:
        raise ImportProblem("No public tracks were returned. Private playlists need to be made public before importing.")
    if len(rows) > MAX_TRACKS:
        raise ImportProblem(f"Import up to {MAX_TRACKS} tracks at a time.")
    tracks = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        uri = row.get("uri", "")
        if not re.fullmatch(r"spotify:track:[A-Za-z0-9]{22}", uri):
            continue
        title, artist = row.get("title"), row.get("subtitle")
        duration = row.get("duration")
        if not isinstance(title, str) or not isinstance(artist, str) or type(duration) not in (int, float):
            continue
        if not title.strip() or not artist.strip() or not 0 < duration <= 1800000:
            continue
        tracks.append({"id": uri.rsplit(":", 1)[1], "title": title[:300], "artist": artist[:300],
                       "duration": round(duration / 1000), "status": "pending", "hash": None, "message": ""})
    if not tracks:
        raise ImportProblem("This playlist has no supported public music tracks.")
    return {"source": source, "name": str(entity.get("title") or entity.get("name") or "Spotify playlist")[:200],
            "tracks": tracks, "artwork": artwork_url(entity),
            "notice": "Spotify shared this public track list. It may omit private, unavailable or additional tracks in large playlists. Check the preview before importing."}


def normal(value):
    value="".join(c for c in unicodedata.normalize("NFKD",value) if not unicodedata.combining(c))
    return " ".join(re.findall(r"\w+",value.casefold()))


def similarity(a, b):
    left,right=normal(a),normal(b)
    return difflib.SequenceMatcher(None,left,right).ratio() if left and right else 0


def library_match(track):
    from swingmusic.store.tracks import TrackStore
    for group in list(TrackStore.trackhashmap.values()):
        item = group.get_best()
        if similarity(item.title, track["title"]) < .94:
            continue
        if not any(similarity(a["name"], track["artist"]) >= .86 or normal(a["name"]) == normal(track["artist"].split(",")[0]) for a in item.artists):
            continue
        if abs(item.duration - track["duration"]) <= max(5, track["duration"] * .04):
            return item.trackhash
    return None


def choose_match(track, entries):
    candidates = []
    for entry in entries:
        if not isinstance(entry, dict) or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(entry.get("id", ""))):
            continue
        length = entry.get("duration")
        if not isinstance(length, (int, float)) or abs(length - track["duration"]) > max(10, track["duration"] * .07):
            continue
        raw_title = entry.get("title") or ""
        if not isinstance(raw_title, str):
            continue
        # Distributor labels are presentation, not part of the song title.
        title = normal(re.sub(r"[\[(](?:official\s+)?(?:audio|music video|video|mv|lyric video|lyrics|visualizer)(?:\s+(?:hd|hq|4k))?[\])]", "", raw_title, flags=re.I))
        wanted = normal(track["title"])
        artists = [normal(a) for a in track["artist"].split(",") if normal(a)]
        if any(word in title.split() and word not in wanted.split() for word in ("cover", "karaoke", "remix", "live", "sped", "slowed", "instrumental", "acoustic")):
            continue
        # Remove only credited artist names and credit markers; retain version
        # words such as remix/live/radio edit when comparing the recording.
        song_title = " "+title+" "
        for artist in sorted(artists, key=len, reverse=True):
            song_title = re.sub(r"(?<!\w)"+re.escape(artist)+r"(?!\w)", " ", song_title)
        song_title = re.sub(r"\b(?:ft|feat|featuring)\b", " ", song_title)
        title_score = max(similarity(title, wanted), similarity(song_title, wanted))
        uploader = entry.get("uploader") or entry.get("channel") or ""
        if not isinstance(uploader, str):
            continue
        uploader = re.sub(r"\s*-\s*Topic$|VEVO$", "", uploader, flags=re.I).strip()
        artist_score = max((max(similarity(artist, uploader), 1.0 if re.search(r"(?<!\w)"+re.escape(artist)+r"(?!\w)", title) else 0) for artist in artists), default=0)
        if title_score < .65 or artist_score < .65:
            continue
        score = title_score * .65 + artist_score * .25 + (1 - abs(length-track["duration"])/max(1,track["duration"])) * .1
        candidates.append((score, entry))
    if not candidates:
        raise ImportProblem("No audio match with the right title, artist and duration was found. Retry later or add this song from your own files.")
    return max(candidates, key=lambda pair: pair[0])[1]


def tool_path(name):
    filename = name + (".exe" if os.name == "nt" else "")
    roots = [Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "import-tools", Path(sys.executable).parent / "import-tools"]
    for root in roots:
        if (root / filename).is_file():
            return str(root / filename)
    found = shutil.which(name)
    if found and not getattr(sys, "frozen", False):
        return found
    raise ImportProblem("Download tools are unavailable. Reinstall the latest Music release.")


def run_tool(arguments, cancelled, timeout):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith(("WORKSPACE_", "GH_", "GITHUB_"))}
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    # Output is spooled privately; neither tool diagnostics nor local paths are exposed in the UI.
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        with subprocess.Popen(arguments, stdout=output, stderr=errors, stdin=subprocess.DEVNULL,
                              env=env, creationflags=flags, start_new_session=os.name != "nt") as process:
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if cancelled.wait(.25) or time.monotonic() > deadline:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
                    else:
                        import signal
                        os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    if cancelled.is_set():
                        raise ImportCancelled()
                    raise ImportProblem("The audio service timed out. Retry this track later.")
            if process.returncode:
                raise ImportProblem("The audio provider could not download this track. It may be unavailable or require sign-in. Retry later.")
            output.seek(0)
            data = output.read(2_000_001)
            if len(data) > 2_000_000:
                raise ImportProblem("The audio provider returned an oversized response.")
            return data.decode("utf-8", "replace")


def search_audio(track, common, cancelled):
    # Unquoted queries can silently autocorrect rare artist/title combinations
    # into popular unrelated songs. Exact terms find distributor Topic uploads.
    title = track["title"].replace('"', ' ')
    artist = track["artist"].split(",")[0].replace('"', ' ')
    queries = [f'"{title}" "{artist}"', artist+" "+track["title"]+" audio"]
    readable = False
    for query in queries:
        if cancelled.is_set():
            raise ImportCancelled()
        result = run_tool(common + ["--flat-playlist", "--dump-single-json", "ytsearch5:"+query], cancelled, 75)
        try:
            data = json.loads(result)
        except (ValueError, TypeError):
            continue
        entries = data.get("entries") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            continue
        readable = True
        try:
            return choose_match(track, entries)
        except ImportProblem:
            continue
    if not readable:
        raise ImportProblem("The audio search returned an unreadable response. Retry later.")
    # Keep match failures distinct from JSON failures (ImportProblem is a ValueError).
    return choose_match(track, [])


def download_audio(track, folder, cancelled):
    ytdlp, node = tool_path("yt-dlp"), tool_path("node")
    ffmpeg = str(Path(getattr(sys, "_MEIPASS", Path(shutil.which("ffmpeg") or "").parent)) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
    common = [ytdlp, "--ignore-config", "--no-plugin-dirs", "--no-cache-dir", "--no-playlist", "--no-warnings", "--no-progress", "--socket-timeout", "15", "--retries", "1", "--extractor-retries", "1", "--js-runtimes", "node:"+node]
    match = search_audio(track, common, cancelled)
    run_tool(common + ["--ffmpeg-location", ffmpeg, "--max-filesize", "80M", "--format", "bestaudio/best", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "192K", "--output", str(folder/"audio.%(ext)s"), "https://www.youtube.com/watch?v="+match["id"]], cancelled, 300)
    file = folder / "audio.mp3"
    if cancelled.is_set():
        raise ImportCancelled()
    if not file.is_file() or not 500 < file.stat().st_size <= 85_000_000:
        raise ImportProblem("No complete audio file was received.")
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, WOAR, APIC, TALB, TDRC
    audio = MP3(file)
    if abs(audio.info.length-track["duration"]) > max(12,track["duration"]*.1):
        raise ImportProblem("The downloaded version has a different duration. It was not added.")
    tags = ID3()
    tags.add(TIT2(encoding=3, text=track["title"]))
    tags.add(TPE1(encoding=3, text=track["artist"]))
    tags.add(WOAR(url="https://open.spotify.com/track/"+track["id"]))
    try:
        entity=entity_from_html(public_bytes("https://open.spotify.com/embed/track/"+track["id"]).decode("utf-8"))
        date=entity.get("releaseDate") or ""
        date=str(date.get("isoString") or "") if isinstance(date,dict) else str(date)
        if re.match(r"^\d{4}",date):
            tags.add(TDRC(encoding=3,text=date[:4]))
        album=entity.get("relatedEntityUri") or ""
        if cancelled.is_set():
            raise ImportCancelled()
        if re.fullmatch(r"spotify:album:[A-Za-z0-9]{22}",album):
            info=entity_from_html(public_bytes("https://open.spotify.com/embed/album/"+album.rsplit(":",1)[1]).decode("utf-8"))
            title=info.get("title") or info.get("name")
            if isinstance(title,str):
                tags.add(TALB(encoding=3,text=title[:300]))
        image=artwork_url(entity)
        if image:
            if cancelled.is_set():
                raise ImportCancelled()
            import io
            with artwork_image(image) as cover:
                cover.thumbnail((600,600))
                result=io.BytesIO();cover.save(result,"JPEG",quality=88)
                tags.add(APIC(encoding=3,mime="image/jpeg",type=3,desc="Cover",data=result.getvalue()))
    except (ImportProblem,requests.RequestException,ValueError,OSError,KeyError,TypeError):
        pass  # Optional cover/album lookup must not discard successfully downloaded audio.
    tags.save(file)
    return file


def music_root():
    from swingmusic.config import UserConfig
    root = os.environ.get("WORKSPACE_MUSIC_DIR")
    if not root:
        roots = UserConfig().rootDirs
        root = next((r for r in roots if r != "$home" and Path(r).is_absolute()), None)
    if not root or not Path(root).is_absolute() or not Path(root).is_dir():
        raise ImportProblem("Choose a music folder in Advanced library settings before downloading.")
    folder = Path(root).resolve() / "Spotify imports"
    if folder.is_symlink():
        raise ImportProblem("The Spotify imports folder must be an ordinary local folder.")
    folder.mkdir(exist_ok=True)
    if folder.resolve().parent != Path(root).resolve():
        raise ImportProblem("The import folder is outside your music library.")
    return folder


class ImportManager:
    def __init__(self, app):
        from swingmusic.settings import Paths
        self.app, self.lock, self.events = app, threading.RLock(), {}
        self.ready = False
        self.path = Paths().config_dir / "music-imports.sqlite3"
        with self.database() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, owner TEXT NOT NULL, data TEXT NOT NULL)")
            if "stop_requested" not in {row[1] for row in db.execute("PRAGMA table_info(jobs)")}:
                db.execute("ALTER TABLE jobs ADD COLUMN stop_requested INTEGER NOT NULL DEFAULT 0")
            for jid, raw, stopped in db.execute("SELECT id,data,stop_requested FROM jobs").fetchall():
                job = json.loads(raw)
                if job["status"] in ACTIVE or (job["status"] == "interrupted" and job.get("mode") and job.get("playlist")):
                    if stopped:
                        job.update(status="cancelled", message="Import stopped. Added songs are kept; resume to continue.")
                    else:
                        job.setdefault("queueOrder", job["created"] * 1_000_000_000)
                        job.update(status="queued", message="Music restarted. Queued to resume automatically.")
                    db.execute("UPDATE jobs SET data=? WHERE id=?", (json.dumps(job), jid))

    @contextmanager
    def database(self):
        connection = sqlite3.connect(self.path, timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def save(self, job):
        with self.database() as db:
            db.execute("INSERT INTO jobs (id,owner,data) VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (job["id"], job["owner"], json.dumps(job)))

    def pending(self):
        with self.database() as db:
            jobs = [json.loads(row[0]) for row in db.execute("SELECT data FROM jobs WHERE stop_requested=0")]
        return sorted((job for job in jobs if job["status"] == "queued"), key=lambda job: (job["queueOrder"], job["id"]))

    def resume_pending(self):
        # Called by the server after database migrations and library stores load,
        # without needing an open browser or an authenticated request.
        with self.lock:
            self.ready = True
            self.dispatch()

    def dispatch(self):
        # All callers hold the manager lock. Reserve the sole worker before
        # starting its thread, including while it is waiting to enter work().
        if not self.ready or self.events:
            return
        for job in self.pending():
            event = threading.Event()
            self.events[job["id"]] = event
            job.update(status="running", message="Importing playlist")
            self.save(job)
            try:
                threading.Thread(target=self.work, args=(job["id"], job["owner"], event), daemon=True, name="spotify-import").start()
                return
            except RuntimeError:
                self.events.pop(job["id"], None)
                job.update(status="failed", message="Could not start this import. Resume to try again.")
                self.save(job)

    def load(self, jid, owner):
        with self.database() as db:
            row = db.execute("SELECT data FROM jobs WHERE id=? AND owner=?", (jid, owner)).fetchone()
        if not row:
            abort(404)
        return json.loads(row[0])

    def public(self, job):
        result = {key: value for key, value in job.items() if key not in ("owner", "user", "playlistKey", "queueOrder")}
        if job["status"] == "queued":
            with self.lock:
                result["queuePosition"] = next((index + 1 for index, item in enumerate(self.pending()) if item["id"] == job["id"]), None)
        result["finished"] = sum(t["status"] in ("existing", "downloaded", "missing", "failed") for t in job["tracks"])
        result["available"] = sum(t["status"] in ("existing", "downloaded") for t in job["tracks"])
        return result

    def preview(self, owner, user, value):
        job = resolve_playlist(value)
        for track in job["tracks"]:
            track["hash"] = library_match(track)
            if track["hash"]:
                track["status"] = "existing"
        job.update(id=secrets.token_hex(16), owner=owner, user=user, status="preview", playlist=None,
                   playlistKey=None, message="Preview ready", created=int(time.time()), mode=None)
        with self.lock:
            self.save(job)
            # Keep the latest twenty completed/draft jobs per principal; active jobs are never pruned.
            with self.database() as db:
                rows = db.execute("SELECT id,data FROM jobs WHERE owner=? ORDER BY rowid DESC", (owner,)).fetchall()
                for jid, raw in rows[20:]:
                    if json.loads(raw)["status"] not in ACTIVE:
                        db.execute("DELETE FROM jobs WHERE id=?", (jid,))
        return self.public(job)

    def start(self, jid, owner, download, retry=False):
        from swingmusic.db.userdata import PlaylistTable
        from swingmusic.db.engine import DbEngine
        from swingmusic.utils.dates import create_new_date
        with self.lock:
            job = self.load(jid, owner)
            if job["status"] in ACTIVE or (job["status"] != "preview" and not retry):
                return self.public(job)
            if retry and job["status"] not in TERMINAL:
                raise ImportProblem("This import is not ready to resume.")
            if download:
                music_root()
            if job["playlist"] is None:
                with DbEngine.manager() as db:
                    prior=db.execute(select(PlaylistTable.id,PlaylistTable.extra).where(PlaylistTable.userid==job["user"],PlaylistTable.extra["spotifyImportJob"].as_string()==jid)).first()
                if prior:
                    job["playlist"],job["playlistKey"]=prior.id,prior.extra["musicShareKey"]
                else:
                    result = PlaylistTable.insert_one({"name":job["name"], "image":None,"last_updated":create_new_date(), "userid":job["user"],"settings":{},"trackhashes":[],"extra":{"spotifyImportJob":jid,"spotifySource":job["source"],"description":"Imported from Spotify"}})
                    job["playlist"] = result.lastrowid
                    with DbEngine.manager() as db:
                        extra=db.execute(select(PlaylistTable.extra).where(PlaylistTable.id==job["playlist"])).scalar()
                    job["playlistKey"] = extra["musicShareKey"]
            with self.database() as db:
                previous = [json.loads(row[0]).get("queueOrder", 0) for row in db.execute("SELECT data FROM jobs")]
                db.execute("UPDATE jobs SET stop_requested=0 WHERE id=?", (jid,))
            order = max(time.time_ns(), max(previous, default=0) + 1)
            job.update(status="queued", message="Queued. This playlist will start automatically.", mode="download" if download else "library", queueOrder=order)
            self.save(job)
            self.resume_pending()
            return self.public(self.load(jid, owner))

    def cancel(self, jid, owner):
        with self.lock:
            job = self.load(jid, owner)
            event = self.events.get(jid)
            if job["status"] in ACTIVE:
                # This marker survives stale worker progress writes and a crash
                # between the stop response and subprocess termination.
                with self.database() as db:
                    db.execute("UPDATE jobs SET stop_requested=1 WHERE id=?", (jid,))
                if event:
                    event.set()
                    job["message"] = "Stopping the current download. Added songs are kept."
                else:
                    job.update(status="cancelled", message="Removed from queue. Resume when you are ready.")
                self.save(job)
                self.dispatch()
            return self.public(job)

    def check_owner(self, job):
        from swingmusic.db.userdata import UserTable,PlaylistTable
        from swingmusic.db.engine import DbEngine
        from swingmusic.listening import principal
        user = UserTable.get_by_id(job["user"])
        if not user or principal(user) != job["owner"]:
            raise ImportCancelled()
        if job["playlist"] is not None:
            with DbEngine.manager() as db:
                extra=db.execute(select(PlaylistTable.extra).where(PlaylistTable.id==job["playlist"],PlaylistTable.userid==job["user"])).scalar()
            if not extra or extra.get("musicShareKey")!=job["playlistKey"]:
                raise ImportCancelled()

    def append(self, job, trackhash):
        from swingmusic.db.userdata import PlaylistTable
        from swingmusic.db.engine import DbEngine
        from swingmusic.utils.dates import create_new_date
        self.check_owner(job)
        with DbEngine.manager(commit=True) as db:
            # Serialize with normal SQLite writers; don't overwrite concurrent playlist edits.
            from sqlalchemy import text
            db.execute(text("BEGIN IMMEDIATE"))
            item = db.execute(select(PlaylistTable).where(PlaylistTable.id==job["playlist"],PlaylistTable.userid==job["user"])).scalar()
            if not item or (item.extra or {}).get("musicShareKey") != job["playlistKey"]:
                raise ImportProblem("The imported playlist was deleted. Start a new import to create another.")
            hashes = list(item.trackhashes or [])
            if trackhash not in hashes:
                db.execute(update(PlaylistTable).where(PlaylistTable.id==item.id).values(trackhashes=hashes+[trackhash],last_updated=create_new_date()))

    def set_artwork(self, job, event=None):
        from swingmusic.settings import Paths
        from swingmusic.db.engine import DbEngine
        from swingmusic.db.userdata import PlaylistTable
        from sqlalchemy import text
        self.check_owner(job)
        if event and event.is_set():
            raise ImportCancelled()
        folder = Paths().playlist_img_path
        with DbEngine.manager() as db:
            item = db.execute(select(PlaylistTable).where(PlaylistTable.id==job["playlist"], PlaylistTable.userid==job["user"])).scalar()
            if item and item.image and (folder / item.image).is_file():
                return "Existing playlist cover kept."
        url = job.get("artwork")
        if not valid_artwork_url(url):
            entity = entity_from_html(public_bytes(playlist_url(job["source"]).replace("/playlist/", "/embed/playlist/")).decode("utf-8"))
            url = artwork_url(entity)
        image = artwork_image(url)
        try:
            self.check_owner(job)
        except BaseException:
            image.close()
            raise
        if event and event.is_set():
            image.close()
            raise ImportCancelled()
        created = []
        try:
            with image, DbEngine.manager(commit=True) as db:
                db.execute(text("BEGIN IMMEDIATE"))
                item = db.execute(select(PlaylistTable).where(PlaylistTable.id==job["playlist"], PlaylistTable.userid==job["user"])).scalar()
                if not item or (item.extra or {}).get("musicShareKey")!=job["playlistKey"]:
                    raise ImportCancelled()
                # A cover uploaded while metadata was being fetched takes priority.
                if item.image and (folder / item.image).is_file():
                    return "Existing playlist cover kept."
                name = "spotify-"+secrets.token_hex(16)+".webp"
                for filename, size in ((name, 800), ("thumb_"+name, 250)):
                    copy = image.copy()
                    try:
                        copy.thumbnail((size, size))
                        with (folder / filename).open("xb") as output:
                            created.append(folder / filename)
                            copy.save(output, "WEBP", quality=88)
                    finally:
                        copy.close()
                db.execute(update(PlaylistTable).where(PlaylistTable.id==item.id).values(image=name,settings={**(item.settings or {}),"square_img":True}))
            return "Playlist artwork imported."
        except BaseException:
            for file in created:
                file.unlink(missing_ok=True)
            raise

    def refresh_artwork(self, jid, owner):
        with self.lock:
            job = self.load(jid, owner)
            if not job.get("playlist") or job["status"] in ACTIVE:
                raise ImportProblem("Wait for the import to finish before refreshing artwork.")
            if self.events:
                raise ImportProblem("Wait for the current import to finish before refreshing artwork.")
            try:
                job["artworkMessage"] = self.set_artwork(job)
            except requests.RequestException:
                raise ImportProblem("Could not reach Spotify artwork. Try again later.") from None
            except OSError:
                raise ImportProblem("Could not save playlist artwork. Check storage and try again.") from None
            except ImportCancelled:
                abort(404)
            self.save(job)
            return self.public(job)

    def work(self, jid, owner, event):
        from swingmusic.settings import Paths
        from swingmusic.store.tracks import TrackStore
        job = None
        try:
            with self.app.app_context():
                with self.lock:
                    job = self.load(jid,owner)
                    if event.is_set():
                        raise ImportCancelled()
                    self.check_owner(job)
                    job.update(status="running",message="Importing playlist")
                    self.save(job)
                try:
                    job["artworkMessage"] = self.set_artwork(job, event)
                except (ImportProblem, requests.RequestException, OSError):
                    job["artworkMessage"] = "Playlist artwork unavailable. Use Refresh artwork to try again."
                with self.lock:
                    self.save(job)
                for index in range(len(job["tracks"])):
                    if event.is_set():
                        raise ImportCancelled()
                    self.check_owner(job)
                    track = job["tracks"][index]
                    if track["status"] in ("downloaded", "existing") and track["hash"] in TrackStore.trackhashmap:
                        self.append(job,track["hash"])
                        continue
                    track.update(status="matching",message="Finding audio",hash=None)
                    with self.lock:
                        self.save(job)
                    try:
                        found = library_match(track)
                        if found:
                            track.update(status="existing",hash=found,message="Already in your library")
                        elif job["mode"] == "library":
                            track.update(status="missing",message="Not in your library")
                        else:
                            folder = music_root()
                            target = folder/(track["id"]+".mp3")
                            if target.is_symlink():
                                raise ImportProblem("The destination is not an ordinary audio file.")
                            if target.exists():
                                from mutagen.mp3 import MP3
                                try:
                                    saved=MP3(target)
                                    source="https://open.spotify.com/track/"+track["id"]
                                    if not saved.tags or source not in [str(tag.url) for tag in saved.tags.getall("WOAR")] or similarity(str(saved.tags.get("TIT2","")),track["title"])<.94:
                                        raise ValueError()
                                except Exception:
                                    raise ImportProblem("A different file already uses this name. It was kept; rename it in your Music folder before retrying.") from None
                            if not target.exists():
                                with tempfile.TemporaryDirectory(prefix="spotify-",dir=Paths().config_dir) as tmp:
                                    track.update(status="downloading",message="Downloading matched audio")
                                    with self.lock:
                                        self.save(job)
                                    audio = download_audio(track,Path(tmp),event)
                                    if event.is_set():
                                        raise ImportCancelled()
                                    partial=folder/("."+secrets.token_hex(16)+".partial")
                                    try:
                                        with partial.open("xb") as stream, audio.open("rb") as source:
                                            shutil.copyfileobj(source,stream)
                                        # Windows rename fails if a file appeared meanwhile; never overwrite owner files.
                                        if os.name == "nt":
                                            partial.rename(target)
                                        else:
                                            os.link(partial,target)
                                    finally:
                                        partial.unlink(missing_ok=True)
                            from swingmusic.lib.watchdogg import add_track
                            add_track(str(target))
                            found=next((g.get_best().trackhash for g in list(TrackStore.trackhashmap.values()) if Path(g.get_best().filepath).resolve()==target.resolve()),None)
                            if not found:
                                raise ImportProblem("Audio was saved but could not be indexed. Refresh your library and retry.")
                            track.update(status="downloaded",hash=found,message="Added to your library")
                        if track["hash"]:
                            self.append(job,track["hash"])
                    except ImportProblem as error:
                        track.update(status="failed",message=str(error))
                    except ImportCancelled:
                        raise
                    except Exception:
                        import logging
                        logging.getLogger(__name__).exception("Spotify import track failed")
                        track.update(status="failed",message="This track could not be imported. Retry it later.")
                    with self.lock:
                        self.save(job)
                job.update(status="partial" if any(t["status"] in ("failed","missing") for t in job["tracks"]) else "complete",message="Import finished")
        except ImportCancelled:
            if job:
                job.update(status="cancelled",message="Import stopped. Added songs are kept; resume to continue.")
        except Exception:
            if job:
                job.update(status="failed",message="Import stopped. Added songs are kept; resume to try unfinished tracks.")
        finally:
            with self.lock:
                if job:
                    self.save(job)
                event.set()
                self.events.pop(jid,None)
                self.dispatch()


def manager():
    return current_app.extensions["spotify_imports"]


imports_api = Blueprint("spotify_imports", __name__, url_prefix="/studio/imports")


@imports_api.before_request
def protect_imports():
    from swingmusic.listening import protect, current_user
    response=protect()
    if "guest" in (current_user.get("roles") or []):
        abort(403)
    return response


@imports_api.after_request
def private_imports(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def install(app, _api=None):
    app.extensions["spotify_imports"] = ImportManager(app)
    app.register_blueprint(imports_api)


@imports_api.errorhandler(ImportProblem)
def import_error(error):
    return {"error":str(error)},400


@imports_api.get("")
def imports():
    from swingmusic.listening import principal, current_user
    service=manager()
    with service.lock:
        with service.database() as db:
            rows=db.execute("SELECT data FROM jobs WHERE owner=? ORDER BY rowid DESC",(principal(current_user),)).fetchall()
        jobs = [json.loads(row[0]) for row in rows]
        return {"jobs":[service.public(job) for index, job in enumerate(jobs) if index < 20 or job["status"] in ACTIVE]}


@imports_api.post("/preview")
def preview():
    from swingmusic.listening import payload, principal, user_id, current_user
    return manager().preview(principal(current_user),user_id(),payload().get("url")),201


@imports_api.get("/<jid>")
def status(jid):
    from swingmusic.listening import principal, current_user
    service=manager()
    return service.public(service.load(jid,principal(current_user)))


@imports_api.post("/<jid>/start")
def start(jid):
    from swingmusic.listening import payload, principal, current_user
    body=payload()
    if type(body.get("download")) is not bool or type(body.get("retry",False)) is not bool:
        abort(400)
    return manager().start(jid,principal(current_user),body["download"],body.get("retry",False)),202


@imports_api.post("/<jid>/cancel")
def cancel(jid):
    from swingmusic.listening import principal, current_user
    return manager().cancel(jid, principal(current_user))


@imports_api.post("/<jid>/artwork")
def refresh_artwork(jid):
    from swingmusic.listening import principal, current_user
    return manager().refresh_artwork(jid, principal(current_user))
