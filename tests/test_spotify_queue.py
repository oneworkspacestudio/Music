"""Durable scheduling against fresh synthetic SQLite users and playlists."""
import copy
import threading
import time

import pytest


@pytest.fixture
def queue_service(tmp_path, monkeypatch):
    from flask import Flask
    from swingmusic.settings import Paths, Singleton
    from swingmusic.db.engine import DbEngine
    from swingmusic.db.userdata import UserTable
    from swingmusic.store.tracks import TrackStore
    from swingmusic import spotify_import as s
    from swingmusic.listening import principal
    monkeypatch.setattr(Singleton, "_instances", {})
    monkeypatch.setattr(DbEngine, "_engine", None)
    monkeypatch.setattr(TrackStore, "trackhashmap", {})
    Paths(config_parent=tmp_path / "private", client_dir=tmp_path / "client")
    from swingmusic.setup import run_setup
    run_setup()
    UserTable.insert_one({"username":"Queue fixture", "password":"synthetic-only", "roles":["admin"], "extra":{}})
    user = UserTable.get_by_username("Queue fixture")
    owner = principal(user)
    monkeypatch.setattr(s, "library_match", lambda track: None)
    monkeypatch.setattr(s.ImportManager, "set_artwork", lambda *args: "Synthetic artwork kept")
    monkeypatch.setattr(s, "resolve_playlist", lambda name: {"name":name, "source":"https://open.spotify.com/playlist/" + "a"*22, "notice":"Fixture", "tracks":[{"id":"b"*22,"title":"Original fixture","artist":"Fixture","duration":65,"status":"pending","hash":None,"message":""}]})
    service = s.ImportManager(Flask(__name__))
    def preview(name):
        return service.preview(owner, user.id, name)["id"]
    yield service, owner, preview
    # Never leave a test worker using a DB after its fixture is reset.
    with service.lock:
        service.ready = False
        for event in service.events.values():
            event.set()
    wait_idle(service)


def wait_idle(service):
    for _ in range(500):
        with service.lock:
            if not service.events:
                return
        time.sleep(.01)
    pytest.fail("Import queue did not settle")


def test_fifo_acceptance_cancel_and_resume(queue_service, monkeypatch):
    service, owner, preview = queue_service
    a, b, c = [preview(name) for name in ("A", "B", "C")]
    entered, gate = threading.Event(), threading.Event()
    original, started = service.work, []
    def work(jid, *args):
        started.append(jid)
        if jid == c:
            entered.set()
            assert gate.wait(5)
        original(jid, *args)
    monkeypatch.setattr(service, "work", work)
    first = service.start(c, owner, False)
    assert entered.wait(2)
    second = service.start(a, owner, False)
    third = service.start(b, owner, False)
    assert first["status"] == "running"
    assert second["queuePosition"] == 1 and third["queuePosition"] == 2
    assert service.start(b, owner, False)["playlist"] == third["playlist"]
    assert len(service.events) == 1
    assert service.cancel(a, owner)["status"] == "cancelled"
    assert service.public(service.load(b, owner))["queuePosition"] == 1
    resumed = service.start(a, owner, False, retry=True)
    assert resumed["playlist"] == second["playlist"] and resumed["queuePosition"] == 2
    gate.set()
    wait_idle(service)
    assert started == [c, b, a]
    assert all(service.load(jid, owner)["status"] == "partial" for jid in (a, b, c))


def test_restart_accepted_work_and_durable_stop(queue_service, monkeypatch):
    from swingmusic import spotify_import as s
    service, owner, preview = queue_service
    a, b, draft = [preview(name) for name in ("Accepted", "Stopped", "Preview")]
    # Persist accepted jobs without dispatch, then simulate process loss while
    # one was running and another stop response had already been acknowledged.
    monkeypatch.setattr(service, "resume_pending", lambda: None)
    accepted = service.start(a, owner, False)
    service.start(b, owner, False)
    for jid in (a, b):
        job = service.load(jid, owner)
        job["status"] = "running"
        service.save(job)
    with service.database() as db:
        db.execute("UPDATE jobs SET stop_requested=1 WHERE id=?", (b,))
    replacement = s.ImportManager(service.app)
    assert replacement.load(a, owner)["status"] == "queued"
    assert replacement.load(b, owner)["status"] == "cancelled"
    assert replacement.load(draft, owner)["status"] == "preview"
    started, original = [], replacement.work
    def work(jid, *args):
        started.append(jid)
        original(jid, *args)
    monkeypatch.setattr(replacement, "work", work)
    replacement.resume_pending()
    replacement.resume_pending()
    wait_idle(replacement)
    assert started == [a]
    assert replacement.load(a, owner)["playlist"] == accepted["playlist"]
    assert replacement.load(a, owner)["status"] == "partial"
    assert replacement.load(b, owner)["status"] == "cancelled"


def test_running_stop_survives_stale_progress_and_next_runs(queue_service, monkeypatch):
    from swingmusic import spotify_import as s
    service, owner, preview = queue_service
    a, b = preview("Running"), preview("Next")
    entered, gate = threading.Event(), threading.Event()
    original = service.set_artwork
    def artwork(job, event):
        if job["id"] == a:
            entered.set()
            assert gate.wait(5)
            if event.is_set():
                raise s.ImportCancelled()
        return original(job, event)
    monkeypatch.setattr(service, "set_artwork", artwork)
    service.start(a, owner, False)
    assert entered.wait(2)
    service.start(b, owner, False)
    stale = copy.deepcopy(service.load(a, owner))
    service.cancel(a, owner)
    service.save(stale)
    with service.database() as db:
        assert db.execute("SELECT stop_requested FROM jobs WHERE id=?", (a,)).fetchone()[0] == 1
    gate.set()
    wait_idle(service)
    assert service.load(a, owner)["status"] == "cancelled"
    assert service.load(b, owner)["status"] == "partial"


def test_deleted_playlist_does_not_block_queue(queue_service, monkeypatch):
    from sqlalchemy import delete
    from swingmusic.db.engine import DbEngine
    from swingmusic.db.userdata import PlaylistTable
    service, owner, preview = queue_service
    a, b = preview("Deleted"), preview("Valid")
    original = service.resume_pending
    monkeypatch.setattr(service, "resume_pending", lambda: None)
    accepted = service.start(a, owner, False)
    service.start(b, owner, False)
    with DbEngine.manager(commit=True) as db:
        db.execute(delete(PlaylistTable).where(PlaylistTable.id == accepted["playlist"]))
    original()
    wait_idle(service)
    assert service.load(a, owner)["status"] == "cancelled"
    assert service.load(b, owner)["status"] == "partial"


def test_active_jobs_survive_history_pruning(queue_service, monkeypatch):
    service, owner, preview = queue_service
    monkeypatch.setattr(service, "resume_pending", lambda: None)
    first = preview("Old accepted job")
    service.start(first, owner, False)
    for index in range(25):
        preview("Draft " + str(index))
    assert service.public(service.load(first, owner))["queuePosition"] == 1


def test_concurrent_duplicate_starts_reserve_one_worker(queue_service, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from swingmusic.db.userdata import PlaylistTable
    service, owner, preview = queue_service
    first, second = preview("First"), preview("Concurrent")
    gate, entered = threading.Event(), threading.Event()
    original, started = service.work, []
    def work(jid, *args):
        started.append(jid)
        if jid == first:
            entered.set()
            assert gate.wait(5)
        original(jid, *args)
    monkeypatch.setattr(service, "work", work)
    service.start(first, owner, False)
    assert entered.wait(2)
    with ThreadPoolExecutor(max_workers=6) as pool:
        replies = list(pool.map(lambda _: service.start(second, owner, False), range(12)))
    assert len({job["playlist"] for job in replies}) == 1
    assert PlaylistTable.count() == 2 and len(service.events) == 1
    gate.set()
    wait_idle(service)
    assert started == [first, second]


def test_legacy_recovery_rechecks_principal_and_keeps_pauses(queue_service, monkeypatch):
    from swingmusic import spotify_import as s
    from swingmusic.db.userdata import UserTable
    from swingmusic.listening import principal
    service, owner, preview = queue_service
    invalid, paused = preview("Legacy interrupted"), preview("Paused")
    monkeypatch.setattr(service, "resume_pending", lambda: None)
    service.start(invalid, owner, False)
    service.start(paused, owner, False)
    for jid, state in ((invalid, "interrupted"), (paused, "cancelled")):
        job = service.load(jid, owner)
        job["status"] = state
        service.save(job)
    # Reusing the old numeric account ID cannot carry its import capability.
    user = UserTable.get_by_username("Queue fixture")
    UserTable.update_one({"id":user.id, "extra":{"musicPrincipal":"0"*64}})
    UserTable.insert_one({"username":"Next account", "password":"synthetic-only", "roles":["user"], "extra":{}})
    other = UserTable.get_by_username("Next account")
    other_owner = principal(other)
    valid = service.preview(other_owner, other.id, "Next valid job")["id"]
    service.start(valid, other_owner, False)
    replacement = s.ImportManager(service.app)
    assert replacement.load(invalid, owner)["status"] == "queued"
    replacement.resume_pending()
    wait_idle(replacement)
    assert replacement.load(invalid, owner)["status"] == "cancelled"
    assert replacement.load(paused, owner)["status"] == "cancelled"
    assert replacement.load(valid, other_owner)["status"] == "partial"
