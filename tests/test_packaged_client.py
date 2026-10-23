"""A packaged custom UI must never be replaced by an upstream download."""
from types import SimpleNamespace
import pytest


def test_frozen_bundle_version_wins_and_mismatches_fail_closed(tmp_path, monkeypatch):
    from swingmusic import settings
    bundle = tmp_path / "bundle";bundle.mkdir()
    client = tmp_path / "client";client.mkdir()
    (bundle / "version.txt").write_text("3.0.1", encoding="utf-8")
    (client / "version.txt").write_text("3.0.0", encoding="utf-8")
    (client / "index.html").write_text("preserve the custom UI", encoding="utf-8")
    monkeypatch.setattr(settings.sys, "frozen", True, raising=False)
    monkeypatch.setattr(settings.sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(settings.metadata, "version", lambda _: "3.0.0")
    monkeypatch.setattr(settings, "Paths", lambda: SimpleNamespace(client_path=client))
    def no_download(*args, **kwargs):
        pytest.fail("A frozen Music build attempted to download upstream UI")
    monkeypatch.setattr(settings.AssetHandler, "download_client_from_github", no_download)
    assert settings.Metadata.version == "3.0.1"
    with pytest.raises(RuntimeError, match="reinstall the verified package"):
        settings.AssetHandler.ensure_client_matches_app_version()
    assert (client / "index.html").read_text() == "preserve the custom UI"
    (client / "version.txt").write_text("3.0.1", encoding="utf-8")
    settings.AssetHandler.ensure_client_matches_app_version()
