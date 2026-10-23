"""Disposable loopback browser fixture. Never point this at an owner data store."""
import argparse
import io
import math
import os
from pathlib import Path
import secrets
import struct
import wave


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--client", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if not str(root).lower().startswith("c:\\projects\\.cache\\music-listening-20261023\\"):
        raise ValueError("Use a new task-owned fixture directory")
    if root.exists():
        raise ValueError("Fixture root must be new")
    secret = os.environ["MY_MUSIC_FIXTURE_SECRET"]
    root.mkdir(parents=True)
    from swingmusic.settings import Paths
    Paths(config_parent=root / "private", client_dir=args.client.resolve())
    from swingmusic.setup import run_setup
    run_setup()
    from swingmusic.config import UserConfig
    music = root / "Music";music.mkdir()
    config = UserConfig();config.rootDirs = [music.as_posix()];config.save()
    from swingmusic.db.userdata import UserTable, PlaylistTable, FavoritesTable
    users = {}
    for name in ("Alex", "Jordan", "Sam"):
        UserTable.insert_one({"username": name, "password": secrets.token_hex(32), "roles": ["admin"] if name == "Alex" else ["user"], "extra": {"workspaceIssuer": "https://synthetic.myaccounts.test", "workspaceSubject": "fixture-" + name, "displayName": name}})
        users[name] = UserTable.get_by_username(name)
    from PIL import Image, ImageDraw, ImageFont
    from swingmusic.models.track import Track
    from swingmusic.store.tracks import TrackStore, TrackGroup
    from swingmusic.db.libdata import TrackTable
    from swingmusic.utils.hashing import create_hash
    albums = [("After Hours", "Luna Park", "#613f87"), ("Sunset Radio", "The Satellites", "#e0831a"), ("Quiet Places", "Mira Sol", "#6594b7"), ("Electric Bloom", "Nova", "#ba344e"), ("Homeward", "Oliver Reed", "#528071"), ("Night Drive", "Neon Coast", "#28508d"), ("Golden", "June Atlas", "#b69c4a"), ("Daydreams", "Cleo", "#b575a0")]
    titles = ["Glass House", "Slow Motion", "Under the Twin Skies", "Every Little Thing", "The Dreaming Nest", "Flowers in the Rain", "A Place for Us", "Still Here", "Into the Blue", "Soft Landing", "Brighter Days", "Out of the City", "Sweet Surrender", "We Could Be", "Northern Lights", "Together Again"]
    hashes = []
    for i, title in enumerate(titles):
        album, artist, color = albums[i % len(albums)]
        file = music / (title + ".wav")
        with wave.open(str(file), "wb") as wav:
            wav.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
            sample = b"".join(struct.pack("<h", int(1200 * math.sin(2 * math.pi * (220 + i * 15) * n / 8000))) for n in range(8000))
            wav.writeframes(sample * 65)
        trackhash = create_hash(title, artist);albumhash = create_hash(album, artist)
        track = Track(id=i+1, title=title, album=album, albumhash=albumhash, artists=artist, albumartists=artist, bitrate=128, copyright="Synthetic fixture audio and artwork", date=2026, disc=1, duration=65, filepath=file.as_posix(), folder=music.as_posix(), genres="Ambient", last_mod=100000-i, track=i+1, trackhash=trackhash, extra={}, lastplayed=0, playcount=0, playduration=0, config=config, color=color, fav_userids=[users["Alex"].id] if i < 8 else [])
        TrackStore.trackhashmap[track.trackhash] = TrackGroup([track]);hashes.append(track.trackhash)
        if i < 8:
            FavoritesTable.insert_one({"hash": "track_" + track.trackhash, "type": "track", "timestamp": i, "userid": users["Alex"].id, "extra": {}})
        image = Image.new("RGB", (512, 512), color);draw = ImageDraw.Draw(image)
        for j in range(16):
            shade = tuple(max(0, int(color[k:k+2], 16) - j * 4) for k in (1, 3, 5))
            draw.rectangle((0, j*32, 512, (j+1)*32), fill=shade)
        draw.ellipse((70, 80, 442, 452), outline="#ffffff88", width=2)
        draw.ellipse((140, 150, 372, 382), fill=color)
        font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 43)
        small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
        words=album.upper().split();draw.multiline_text((32, 30), "\n".join(words), font=font, fill="white", spacing=0)
        draw.text((32, 468), artist.upper(), font=small, fill="white")
        for folder in (Paths().md_thumb_path, Paths().lg_thumb_path, Paths().sm_thumb_path, Paths().xsm_thumb_path):
            folder.mkdir(parents=True, exist_ok=True);image.save(folder / (albumhash + ".webp"))
        file.with_suffix(".lrc").write_text("[00:00.00]Original synthetic lyric fixture\n[00:05.00]A little song to try the player\n[00:10.00]Every line belongs to this test\n[00:15.00]And the music carries on", encoding="utf-8")
    for i, name in enumerate(("Dance", "Sleep", "Sweet Lullabies", "The Late Shift", "Sunday Morning", "On Repeat")):
        PlaylistTable.insert_one({"name": name, "image": None, "last_updated": "2026-10-23 10:00:00", "userid": users["Alex"].id, "settings": {}, "trackhashes": hashes[i:i+9], "extra": {"description": "A handpicked mix for the moments in between."}})
    from swingmusic.store.general import GeneralStore
    GeneralStore.admin_exists = True;GeneralStore.root_dirs_set = True
    from swingmusic import app_builder
    app = app_builder.build()
    from flask import request, abort, redirect
    from flask_jwt_extended import create_access_token, set_access_cookies
    @app.get("/fixture/login")
    def fixture_login():
        if not secrets.compare_digest(request.args.get("key", ""), secret):
            abort(404)
        user = users.get(request.args.get("account"))
        if not user:
            abort(404)
        response = redirect("/music/");set_access_cookies(response, create_access_token(identity=user.todict()))
        return response
    # The synthetic bootstrap route is not a production route and is explicitly
    # permitted only inside this disposable process.
    app.before_request_funcs[None].insert(0, lambda: None)
    original = app_builder.check_auth_need
    app_builder.check_auth_need = lambda: request.path == "/fixture/login" or original()
    from werkzeug.middleware.dispatcher import DispatcherMiddleware
    from werkzeug.wrappers import Response
    from waitress import serve
    print("Synthetic music fixture ready", flush=True)
    serve(DispatcherMiddleware(Response("Not found", 404), {"/music": app}), host="127.0.0.1", port=39124)


if __name__ == "__main__":
    main()
