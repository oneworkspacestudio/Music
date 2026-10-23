"""Real SQLite ownership/grants and signed JWTs, with synthetic indexed tracks."""
import json
from types import SimpleNamespace


def test_read_only_sharing_and_account_boundaries(tmp_path, monkeypatch):
    from flask import Flask
    from flask_jwt_extended import JWTManager, create_access_token
    from swingmusic.settings import Paths
    Paths(config_parent=tmp_path / "private", client_dir=tmp_path / "client")
    from swingmusic.setup import run_setup
    run_setup()
    from swingmusic.db.userdata import UserTable, PlaylistTable, FavoritesTable
    from swingmusic.listening import install
    from swingmusic.store.tracks import TrackStore
    users = []
    for name, issuer in [("Owner", "https://accounts.test"), ("Listener", "https://accounts.test"), ("Stranger", "https://accounts.test"), ("Other issuer", "https://elsewhere.test")]:
        UserTable.insert_one({"username": name, "password": "not-a-real-password", "roles": ["user"], "extra": {"workspaceIssuer": issuer, "workspaceSubject": name, "displayName": name}})
        users.append(UserTable.get_by_username(name))
    track = SimpleNamespace(trackhash="a" * 16, title="Synthetic song", album="Fixture album", albumhash="b" * 16, artists=[{"name": "Test artist"}], duration=60, image="b.webp", color="#773333", date=2026, explicit=False, fav_userids=[users[0].id], last_mod=1)
    TrackStore.trackhashmap = {track.trackhash: SimpleNamespace(get_best=lambda: track)}
    FavoritesTable.insert_one({"hash": "track_" + track.trackhash, "type": "track", "timestamp": 1, "userid": users[0].id, "extra": {}})
    PlaylistTable.insert_one({"name": "Private playlist", "image": None, "last_updated": "2026-10-23 10:00:00", "userid": users[0].id, "settings": {}, "trackhashes": [track.trackhash], "extra": {}})
    from sqlalchemy import insert, select
    # Simulate a legacy playlist owned by somebody other than fallback user 1.
    next(PlaylistTable.execute(insert(PlaylistTable).values(name="Legacy listener mix", image=None, last_updated="2026-10-23 10:00:00", userid=users[1].id, settings={}, trackhashes=[], extra={}), commit=True))
    app = Flask(__name__);app.config.update(JWT_SECRET_KEY="synthetic-signing-key-for-tests-only", JWT_VERIFY_SUB=False)
    jwt = JWTManager(app)
    @jwt.user_lookup_loader
    def lookup(_header, data):
        user = UserTable.get_by_id(data["sub"]["id"])
        return user.todict() if user else None
    install(app)
    rows = next(PlaylistTable.execute(select(PlaylistTable.extra))).scalars()
    assert all(len(extra["musicShareKey"]) == 64 for extra in rows)
    clients = [app.test_client() for _ in users]
    headers = []
    for client, user in zip(clients, users):
        with app.app_context():
            token = create_access_token(identity=user.todict())
        header = {"Authorization": "Bearer " + token, "Origin": "http://localhost"}
        boot = client.get("/studio/bootstrap", headers=header).get_json()
        header["X-Music-CSRF"] = boot["csrf"]
        headers.append(header)
    owner, listener, stranger, other = clients
    playlist = owner.get("/studio/bootstrap", headers=headers[0]).get_json()["collections"][-1]
    resource = f"/studio/collections/{users[0].id}/playlist/{playlist['id']}"
    share = f"/studio/shares/playlist/{playlist['id']}"
    assert owner.put(f"/studio/shares/playlist/0{playlist['id']}", headers=headers[0], json={"recipients": [users[1].id]}).status_code == 404
    assert app.test_client().get(resource).status_code == 401
    assert listener.get(resource, headers=headers[1]).status_code == 404
    assert owner.put(share, headers={k: v for k, v in headers[0].items() if k != "X-Music-CSRF"}, json={"recipients": [users[1].id]}).status_code == 403
    assert owner.put(share, headers={**headers[0], "Origin": "https://attacker.test"}, json={"recipients": [users[1].id]}).status_code == 403
    assert owner.put(share, headers=headers[0], json={"recipients": [users[3].id]}).status_code == 400
    assert owner.put(share, headers=headers[0], json={"recipients": [users[1].id]}).status_code == 200
    assert listener.get(resource, headers=headers[1]).get_json()["tracks"][0]["title"] == track.title
    assert listener.get("/studio/bootstrap", headers=headers[1]).get_json()["shared"][0]["editable"] is False
    assert stranger.get(resource, headers=headers[2]).status_code == 404
    assert listener.put(f"/studio/playlists/{playlist['id']}", headers=headers[1], json={"name": "Stolen"}).status_code == 404
    assert listener.delete(f"/studio/playlists/{playlist['id']}", headers=headers[1], json={}).status_code == 404
    # Re-sharing their own resource ID cannot extend another owner's grant.
    assert listener.put(share, headers=headers[1], json={"recipients": [users[2].id]}).status_code == 404
    assert owner.put(share, headers=headers[0], json={"recipients": []}).status_code == 200
    assert listener.get(resource, headers=headers[1]).status_code == 404
    for kind in ("saved", "all"):
        endpoint = "/studio/shares/library/" + kind
        assert owner.put(endpoint, headers=headers[0], json={"recipients": [users[1].id]}).status_code == 200
        shared = listener.get(f"/studio/collections/{users[0].id}/library/{kind}", headers=headers[1]).get_json()
        assert shared["count"] == 1
        assert shared["editable"] is False
    # Personal likes are independent, including when two members like the same song.
    for i in (0, 1):
        assert clients[i].put("/studio/liked/" + track.trackhash, headers=headers[i], json={"liked": True}).status_code == 200
    owner.put("/studio/liked/" + track.trackhash, headers=headers[0], json={"liked": False})
    assert owner.get("/studio/bootstrap", headers=headers[0]).get_json()["liked"] == []
    assert listener.get("/studio/bootstrap", headers=headers[1]).get_json()["liked"] == [track.trackhash]
    assert listener.get(f"/studio/collections/{users[0].id}/library/saved", headers=headers[1]).get_json()["count"] == 0
    assert owner.get("/studio/people", headers=headers[0]).get_json()["people"] == [{"id": users[1].id, "name": "Listener"}, {"id": users[2].id, "name": "Stranger"}]
    # Persistence survives a new SQLite connection; no anonymous/bearer share URL.
    assert listener.get(f"/studio/collections/{users[0].id}/library/all", headers=headers[1]).status_code == 200
    assert stranger.get(f"/studio/collections/{users[0].id}/library/all", headers=headers[2]).status_code == 404
    # A recycled SQLite ID cannot transfer old grants, likes, or an old JWT.
    assert owner.put(share, headers=headers[0], json={"recipients": [users[1].id]}).status_code == 200
    UserTable.remove_by_username("Listener")
    UserTable.insert_one({"id": users[1].id, "username": "Replacement", "password": "synthetic", "roles": ["user"], "extra": {"workspaceIssuer": "https://accounts.test", "workspaceSubject": "replacement"}})
    assert listener.get("/studio/bootstrap", headers=headers[1]).status_code == 401
    replacement = UserTable.get_by_id(users[1].id)
    with app.app_context():
        token = create_access_token(identity=replacement.todict())
    replacement_header = {"Authorization": "Bearer " + token}
    boot = stranger.get("/studio/bootstrap", headers=replacement_header).get_json()
    assert boot["shared"] == [] and boot["liked"] == []
    assert stranger.get(resource, headers=replacement_header).status_code == 404
    assert owner.get(share, headers=headers[0]).get_json()["recipients"] == []
    # Deletion through the classic/native DB path cannot transfer an old grant
    # to a fresh playlist that happens to reuse its ID.
    assert owner.put(share, headers=headers[0], json={"recipients": [users[2].id]}).status_code == 200
    PlaylistTable.remove_one(int(playlist["id"]))
    PlaylistTable.insert_one({"id": int(playlist["id"]), "name": "Replacement playlist", "image": None, "last_updated": "2026-10-23 10:00:00", "userid": users[0].id, "settings": {}, "trackhashes": [track.trackhash], "extra": {}})
    assert stranger.get(resource, headers=headers[2]).status_code == 404
    assert stranger.get("/studio/bootstrap", headers=headers[2]).get_json()["shared"] == []
