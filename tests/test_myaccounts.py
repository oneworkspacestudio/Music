"""Real signed OIDC tokens and a disposable SQLite library; no live provider."""
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa


def test_signed_oidc_and_account_boundary(tmp_path, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_numbers()
    b64 = lambda n: base64.urlsafe_b64encode(n.to_bytes((n.bit_length()+7)//8, "big")).decode().rstrip("=")
    state = {"aud": "music-test", "subject": "ordinary-user", "nonce": ""}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_): pass
        def do_GET(self):
            if self.path == "/.well-known/openid-configuration":
                self.send_json({"issuer": issuer, "authorization_endpoint": issuer+"/authorize", "token_endpoint": issuer+"/token", "jwks_uri": issuer+"/jwks", "response_types_supported": ["code"], "subject_types_supported": ["public"], "id_token_signing_alg_values_supported": ["RS256"]})
            else:
                self.send_json({"keys": [{"kty":"RSA", "kid":"test", "use":"sig", "alg":"RS256", "n":b64(public.n), "e":b64(public.e)}]})
        def do_POST(self):
            body = parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
            assert body.get("code_verifier"), "PKCE verifier missing"
            claims = {"iss":issuer,"aud":state["aud"],"sub":state["subject"],"nonce":state["nonce"],"iat":int(time.time()),"exp":int(time.time())+600,"email":"shared@example.invalid"}
            token = jwt.encode(claims,key,algorithm="RS256",headers={"kid":"test"})
            self.send_json({"access_token":"test-access", "token_type":"Bearer", "id_token":token})
        def send_json(self, data):
            self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers(); self.wfile.write(json.dumps(data).encode())
    server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
    issuer = f"http://127.0.0.1:{server.server_port}"
    threading.Thread(target=server.serve_forever,daemon=True).start()
    for name, value in {"WORKSPACE_OIDC_ISSUER":issuer,"WORKSPACE_OIDC_CLIENT_ID":"music-test","WORKSPACE_OIDC_CLIENT_SECRET":"synthetic-secret","WORKSPACE_OIDC_REDIRECT_URI":"http://localhost:18930/music/auth/myaccounts/callback","WORKSPACE_BASE_PATH":"/music","WORKSPACE_MUSIC_DIR":str(tmp_path/"files/Music"),"WORKSPACE_OWNER_SUBJECT":"actual-owner"}.items():
        monkeypatch.setenv(name,value)
    from swingmusic.settings import Paths
    Paths(config_parent=tmp_path/"private", client_dir=tmp_path/"client")
    from swingmusic.setup import run_setup
    run_setup()
    from swingmusic.myaccounts import prepare_workspace, resolve_user
    prepare_workspace()
    from swingmusic import app_builder
    app = app_builder.build(); app.testing=True
    client = app.test_client()
    # Test client requests carry the public prefix through SCRIPT_NAME while upstream paths stay stripped.
    def get(path):
        return client.get(path,base_url="http://localhost:18930",environ_overrides={"SCRIPT_NAME":"/music"})
    try:
        assert get("/healthz").status_code==200
        assert b"Sign in with MyAccounts" in get("/").data
        assert get("/img/thumbnail/private.webp").status_code==401
        assert get("/studio/bootstrap").status_code==401
        assert get("/auth/myaccounts/callback?state=wrong&code=fake").status_code==401
        def login():
            link = get("/auth/myaccounts/login")
            assert link.status_code==302
            query=parse_qs(urlsplit(link.location).query)
            assert query["code_challenge_method"]==["S256"]
            state["nonce"]=query["nonce"][0]
            return get("/auth/myaccounts/callback?code=test-code&state="+query["state"][0])
        state["aud"]="wrong-client"
        assert login().status_code==401
        state["aud"]="music-test"
        success=login()
        assert success.status_code==302 and success.location=="/music/"
        cookies=success.headers.getlist("Set-Cookie")
        assert any("HttpOnly" in c and "Path=/music/" in c for c in cookies)
        user=resolve_user(issuer,"ordinary-user")
        assert user.roles==["user"]
        assert resolve_user(issuer,"ordinary-user").id==user.id
        # Same mutable email from another subject never links accounts or grants admin.
        assert resolve_user(issuer,"another-user").id!=user.id
        assert resolve_user(issuer,"actual-owner").roles==["admin"]
        assert client.post("/auth/profile/create",json={}).status_code==403
        assert client.post("/notsettings/update",json={}).status_code==403
        # The issued cookie cannot be replayed as a first-user/bootstrap bypass.
        from swingmusic.config import UserConfig
        assert UserConfig().rootDirs==[(tmp_path/"files/Music").resolve().as_posix()]
        from http.cookies import SimpleCookie
        issued = SimpleCookie()
        for cookie in cookies:
            issued.load(cookie)
        signed_headers = {"Authorization": "Bearer " + issued["access_token_cookie"].value}
        assert client.get("/studio/bootstrap", headers=signed_headers).status_code == 200
        from swingmusic.db.userdata import UserTable
        UserTable.remove_by_username(user.username)
        UserTable.insert_one({"id": user.id, "username": "replacement", "password": "synthetic", "roles": ["user"], "extra": {"workspaceIssuer": issuer, "workspaceSubject": "replacement"}})
        denied = client.get("/studio/bootstrap", headers=signed_headers)
        assert denied.status_code == 401
    finally:
        server.shutdown()
