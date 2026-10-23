"""My Music listening UI API and account-bound, read-only collection sharing.

The indexed server music folder retains its existing shared-user semantics.
Grants share playlists or a library view, never filesystem paths or login tokens.
"""
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, jsonify, request, send_file
from flask_jwt_extended import current_user, get_jwt_identity, verify_jwt_in_request, unset_jwt_cookies
from sqlalchemy import select, update

from swingmusic.db.userdata import PlaylistTable, UserTable, ScrobbleTable, FavoritesTable
from swingmusic.db.utils import playlist_to_dataclass
from swingmusic.settings import Paths
from swingmusic.store.tracks import TrackStore

api = Blueprint("listening", __name__, url_prefix="/studio")


@contextmanager
def database():
    with sqlite3.connect(Paths().config_dir / "music-sharing.sqlite3", timeout=15) as db:
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("CREATE TABLE IF NOT EXISTS grants_v2 (owner TEXT NOT NULL, kind TEXT NOT NULL, resource TEXT NOT NULL, recipient TEXT NOT NULL, owner_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL, created INTEGER NOT NULL, PRIMARY KEY(owner,kind,resource,recipient))")
        db.execute("CREATE INDEX IF NOT EXISTS grants_v2_recipient ON grants_v2(recipient)")
        db.execute("CREATE TABLE IF NOT EXISTS likes_v2 (owner TEXT NOT NULL, track TEXT NOT NULL, liked INTEGER NOT NULL, PRIMARY KEY(owner,track))")
        yield db


def principal(user):
    if not user:
        return None
    extra = (user.get("extra") if isinstance(user, dict) else user.extra) or {}
    issuer, subject = extra.get("workspaceIssuer"), extra.get("workspaceSubject")
    if isinstance(issuer, str) and issuer and isinstance(subject, str) and subject:
        value = json.dumps([issuer, subject], separators=(",", ":")).encode()
        return "oidc:" + hashlib.sha256(value).hexdigest()
    if issuer or subject:
        return None
    incarnation = extra.get("musicPrincipal")
    return "local:" + incarnation if isinstance(incarnation, str) and len(incarnation) == 64 else None


def user_id():
    # Unlike the upstream migration helper, never fall back to user 1.
    if not current_user or not isinstance(current_user.get("id"), int):
        abort(401)
    return current_user["id"]


def csrf():
    secret = str(current_app.config["JWT_SECRET_KEY"]).encode()
    return hmac.new(secret, f"my-music-ui:{principal(current_user)}".encode(), hashlib.sha256).hexdigest()


@api.before_request
def protect():
    verify_jwt_in_request()
    user_id()
    claimed, actual = principal(get_jwt_identity()), principal(current_user)
    if not claimed or claimed != actual:
        abort(401)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        public = os.environ.get("WORKSPACE_OIDC_REDIRECT_URI", "")
        parsed = urlsplit(public)
        expected = parsed.scheme + "://" + parsed.netloc if public else request.host_url.rstrip("/")
        if request.headers.get("Origin") != expected or not hmac.compare_digest(request.headers.get("X-Music-CSRF", ""), csrf()):
            abort(403)
        if request.content_length and request.content_length > 512 * 1024:
            abort(413)


@api.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


def payload():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        abort(400)
    return body


@api.errorhandler(400)
@api.errorhandler(403)
@api.errorhandler(404)
def error_response(error):
    return jsonify(error={400: "Invalid request", 403: "Access denied", 404: "Collection unavailable"}[error.code]), error.code


def person(user):
    return {"id": user.id, "name": (user.extra or {}).get("displayName") or (user.extra or {}).get("firstname") or user.username}


def track_data(track):
    return {"hash": track.trackhash, "title": track.title, "album": track.album,
            "albumhash": track.albumhash, "artists": [a["name"] for a in track.artists],
            "artistIds": [a.get("artisthash", "") for a in track.artists],
            "duration": track.duration, "image": track.image, "color": track.color,
            "year": str(track.date or "")[:4], "explicit": track.explicit}


def tracks(hashes):
    return [TrackStore.trackhashmap[h].get_best() for h in hashes if h in TrackStore.trackhashmap]


def liked_hashes(owner):
    legacy = FavoritesTable.execute(select(FavoritesTable.hash).where(FavoritesTable.userid == owner, FavoritesTable.type == "track"))
    result = {value.removeprefix("track_") for value in next(legacy).scalars() if isinstance(value, str)}
    owner_key = principal(UserTable.get_by_id(owner))
    with database() as db:
        for track, liked in db.execute("SELECT track,liked FROM likes_v2 WHERE owner=?", (owner_key,)):
            if liked:
                result.add(track)
            else:
                result.discard(track)
    return result


def playlist(owner, resource):
    if len(resource) > 19 or not resource.isascii() or not resource.isdecimal() or str(int(resource)) != resource or int(resource) < 1:
        abort(404)
    result = PlaylistTable.execute(select(PlaylistTable).where(PlaylistTable.id == int(resource), PlaylistTable.userid == owner))
    row = next(result).scalar()
    if row is None:
        abort(404)
    return playlist_to_dataclass(row)


def resource_data(owner, kind, resource, full=False):
    owner_user = UserTable.get_by_id(owner)
    if owner_user is None:
        abort(404)
    if kind == "playlist":
        item = playlist(owner, resource)
        name, hashes, description = item.name, item.trackhashes, (item.extra or {}).get("description", "")
    elif kind == "library" and resource in ("saved", "all"):
        name = "Liked Songs" if resource == "saved" else "Song library"
        hashes = sorted(liked_hashes(owner)) if resource == "saved" else list(TrackStore.trackhashmap)
        description = "Your saved favourites, all together." if resource == "saved" else "Music indexed from this server’s Music folder."
    else:
        abort(404)
    found = tracks(hashes)
    images = [t.image for t in found[:4]]
    if kind == "playlist" and item.has_image:
        images = ["@playlist/" + item.thumb]
    result = {"owner": owner, "ownerName": person(owner_user)["name"], "kind": kind, "id": resource,
              "name": name, "description": description, "count": len(found), "duration": sum(t.duration for t in found),
              "images": images, "editable": owner == user_id() and kind == "playlist",
              "shared": owner != user_id()}
    if full:
        result["tracks"] = [track_data(t) for t in found]
    return result


def require_read(owner, kind, resource):
    if owner != user_id():
        owner_key = principal(UserTable.get_by_id(owner))
        with database() as db:
            grant = db.execute("SELECT 1 FROM grants_v2 WHERE owner=? AND kind=? AND resource=? AND recipient=?", (owner_key, kind, grant_resource(owner, kind, resource), principal(current_user))).fetchone()
        if not grant:
            abort(404)


def grant_resource(owner, kind, resource):
    if kind != "playlist":
        return resource
    nonce = (playlist(owner, resource).extra or {}).get("musicShareKey")
    if not isinstance(nonce, str) or len(nonce) != 64:
        abort(404)
    return resource + ":" + nonce


@api.get("/bootstrap")
def bootstrap():
    owner = user_id()
    mine = [resource_data(owner, "library", key) for key in ("saved", "all")]
    mine += [resource_data(owner, "playlist", str(p.id)) for p in sorted(PlaylistTable.get_all(), key=lambda p: str(p.last_updated), reverse=True)]
    shared = []
    with database() as db:
        grants = db.execute("SELECT owner_id,kind,resource,owner FROM grants_v2 WHERE recipient=? ORDER BY created DESC", (principal(current_user),)).fetchall()
    for owner_id, kind, resource, owner_key in grants:
        try:
            identifier = resource.split(":", 1)[0]
            if principal(UserTable.get_by_id(owner_id)) == owner_key and grant_resource(owner_id, kind, identifier) == resource:
                shared.append(resource_data(owner_id, kind, identifier))
        except Exception as error:
            from werkzeug.exceptions import NotFound
            if not isinstance(error, NotFound):
                raise
    liked = sorted(liked_hashes(owner))
    recent = list(dict.fromkeys(s.trackhash for s in ScrobbleTable.get_all(0, 60)))
    stamp = str(len(TrackStore.trackhashmap)) + ":" + str(max((getattr(g.get_best(), "last_mod", 0) or 0 for g in TrackStore.trackhashmap.values()), default=0))
    return {"user": person(UserTable.get_by_id(owner)), "csrf": csrf(), "collections": mine,
            "shared": shared, "liked": liked, "likedPreview": [track_data(t) for t in tracks(liked[:40])],
            "recent": [track_data(t) for t in tracks(recent)], "libraryStamp": stamp,
            "myaccounts": bool(os.environ.get("WORKSPACE_OIDC_ISSUER")),
            "scanning": __import__("swingmusic.store.general", fromlist=["GeneralStore"]).GeneralStore.full_scan_in_progress}


@api.get("/tracks")
def list_tracks():
    try:
        start = max(0, int(request.args.get("start", 0)))
        limit = min(500, max(1, int(request.args.get("limit", 100))))
    except ValueError:
        abort(400)
    query = request.args.get("q", "").strip().casefold()[:200]
    album = request.args.get("album", "")
    artist = request.args.get("artist", "").casefold()
    found = (g.get_best() for g in TrackStore.trackhashmap.values())
    found = [t for t in found if (not query or query in (t.title + " " + t.album + " " + " ".join(a["name"] for a in t.artists)).casefold()) and (not album or t.albumhash == album) and (not artist or any(a["name"].casefold() == artist for a in t.artists))]
    found.sort(key=lambda t: (-(getattr(t, "last_mod", 0) or 0), t.title.casefold(), t.trackhash))
    return {"tracks": [track_data(t) for t in found[start:start + limit]], "total": len(found), "start": start}


@api.get("/tracks/<trackhash>")
def get_track(trackhash):
    group = TrackStore.trackhashmap.get(trackhash)
    if not group:
        abort(404)
    return track_data(group.get_best())


@api.get("/collections/<int:owner>/<kind>/<resource>")
def collection(owner, kind, resource):
    require_read(owner, kind, resource)
    return resource_data(owner, kind, resource, True)


@api.get("/people")
def people():
    issuer = (current_user.get("extra") or {}).get("workspaceIssuer")
    query = request.args.get("q", "").casefold()[:100]
    found = [person(u) for u in UserTable.get_all() if u.id != user_id() and "guest" not in u.roles and (not issuer or (u.extra or {}).get("workspaceIssuer") == issuer)]
    return {"people": [u for u in found if query in u["name"].casefold()][:100], "registeredOnly": True}


def valid_recipients(ids):
    if not isinstance(ids, list) or len(ids) > 100 or any(type(i) is not int for i in ids):
        abort(400)
    issuer = (current_user.get("extra") or {}).get("workspaceIssuer")
    for recipient in ids:
        user = UserTable.get_by_id(recipient)
        if not user or recipient == user_id() or "guest" in user.roles or (issuer and (user.extra or {}).get("workspaceIssuer") != issuer):
            abort(400)
    return sorted(set(ids))


@api.route("/shares/<kind>/<resource>", methods=["GET", "PUT"])
def shares(kind, resource):
    owner = user_id()
    owner_key = principal(current_user)
    resource_data(owner, kind, resource)  # only the owner can grant or revoke
    resource = grant_resource(owner, kind, resource)
    with database() as db:
        if request.method == "PUT":
            ids = valid_recipients(payload().get("recipients"))
            db.execute("DELETE FROM grants_v2 WHERE owner=? AND kind=? AND resource=?", (owner_key, kind, resource))
            db.executemany("INSERT INTO grants_v2 VALUES (?,?,?,?,?,?,?)", [(owner_key, kind, resource, principal(UserTable.get_by_id(r)), owner, r, int(time.time())) for r in ids])
        rows = db.execute("SELECT recipient_id,recipient FROM grants_v2 WHERE owner=? AND kind=? AND resource=?", (owner_key, kind, resource)).fetchall()
    return {"recipients": [person(u) for row in rows if (u := UserTable.get_by_id(row[0])) and principal(u) == row[1]], "permission": "view-and-play"}


@api.post("/playlists")
def create_playlist():
    from swingmusic.api.playlist import insert_playlist
    name = payload().get("name", "")
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        abort(400)
    item = insert_playlist(name.strip())
    if item is None:
        abort(400)
    return resource_data(user_id(), "playlist", str(item.id), True), 201


@api.route("/playlists/<int:playlist_id>", methods=["PUT", "DELETE"])
def edit_playlist(playlist_id):
    item = playlist(user_id(), str(playlist_id))
    if request.method == "DELETE":
        # Base.remove_one is intentionally unscoped; ownership is checked above.
        PlaylistTable.remove_one(playlist_id)
        with database() as db:
            db.execute("DELETE FROM grants_v2 WHERE owner=? AND kind='playlist' AND resource=?", (principal(current_user), str(playlist_id) + ":" + item.extra["musicShareKey"]))
        return {"deleted": True}
    body = payload()
    update = {}
    if "name" in body:
        if not isinstance(body["name"], str) or not body["name"].strip() or len(body["name"]) > 200:
            abort(400)
        update["name"] = body["name"].strip()
    if "description" in body:
        if not isinstance(body["description"], str) or len(body["description"]) > 2000:
            abort(400)
        update["extra"] = {**(item.extra or {}), "description": body["description"]}
    if "tracks" in body:
        hashes = body["tracks"]
        if not isinstance(hashes, list) or len(hashes) > 10000 or any(not isinstance(h, str) or h not in TrackStore.trackhashmap for h in hashes):
            abort(400)
        update["trackhashes"] = list(dict.fromkeys(hashes))
    if not update:
        abort(400)
    from swingmusic.utils.dates import create_new_date
    update["last_updated"] = create_new_date()
    PlaylistTable.update_one(playlist_id, update)
    return resource_data(user_id(), "playlist", str(playlist_id), True)


@api.put("/liked/<trackhash>")
def like_track(trackhash):
    liked = payload().get("liked")
    if trackhash not in TrackStore.trackhashmap or type(liked) is not bool:
        abort(400)
    with database() as db:
        db.execute("INSERT INTO likes_v2 VALUES (?,?,?) ON CONFLICT(owner,track) DO UPDATE SET liked=excluded.liked", (principal(current_user), trackhash, int(liked)))
    return {"liked": liked}


@api.get("/audio/<trackhash>")
def audio(trackhash):
    from swingmusic.utils.paths import is_path_within_root_dirs
    group = TrackStore.trackhashmap.get(trackhash)
    if not group:
        abort(404)
    track = group.get_best()
    if not is_path_within_root_dirs(track.filepath) or not os.path.isfile(track.filepath):
        abort(404)
    response = send_file(track.filepath, conditional=True)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@api.get("/lyrics/<trackhash>")
def lyrics(trackhash):
    from swingmusic.api.lyrics import send_lyrics, SendLyricsBody
    group = TrackStore.trackhashmap.get(trackhash)
    if not group:
        abort(404)
    return send_lyrics(SendLyricsBody(trackhash=trackhash, filepath=group.get_best().filepath))


@api.post("/listen")
def record_listen():
    from swingmusic.api.scrobble import log_track, LogTrackBody
    body = payload()
    trackhash, seconds = body.get("track"), body.get("seconds")
    if not isinstance(trackhash, str) or trackhash not in TrackStore.trackhashmap or type(seconds) is not int or not 5 <= seconds <= 86400:
        abort(400)
    return log_track(LogTrackBody(trackhash=trackhash, timestamp=int(time.time()) - seconds, duration=seconds, source="my-music"))


@api.post("/logout")
def logout():
    response = jsonify(signedOut=True)
    unset_jwt_cookies(response)
    return response


def install(app):
    for user in UserTable.get_all():
        extra = dict(user.extra or {})
        if not extra.get("workspaceIssuer") and not extra.get("workspaceSubject") and not extra.get("musicPrincipal"):
            extra["musicPrincipal"] = secrets.token_hex(32)
            UserTable.update_one({"id": user.id, "extra": extra})
    for item in PlaylistTable.get_all(current_user=False):
        if not (item.extra or {}).get("musicShareKey"):
            next(PlaylistTable.execute(update(PlaylistTable).where(PlaylistTable.id == item.id).values(extra={**(item.extra or {}), "musicShareKey": secrets.token_hex(32)}), commit=True))
    app.register_blueprint(api)
