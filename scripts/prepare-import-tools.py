"""Fetch pinned official Windows import tools; never download runtime code on demand."""
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

TOOLS = {
    "yt-dlp.exe": ("https://github.com/yt-dlp/yt-dlp/releases/download/2026.10.21/yt-dlp.exe", "33121d192d706e62f684a06f80918e3f3a8ba52ac3a65213b6951c39c7d9f555"),
    "node.exe": ("https://nodejs.org/dist/v26.8.2/win-x64/node.exe", "23062343ad39fc79f12ae39cfb324e93a20ced5f1d342e7b850c148c022ddbca"),
}
folder = Path(sys.argv[1])
folder.mkdir(parents=True,exist_ok=True)
receipt = {}
for name,(url,expected) in TOOLS.items():
    file=folder/name
    if not file.exists():
        with urllib.request.urlopen(url,timeout=60) as response, file.open("xb") as output:
            import shutil
            shutil.copyfileobj(response,output)
    actual=hashlib.sha256(file.read_bytes()).hexdigest()
    if actual!=expected:
        raise SystemExit("Pinned import tool checksum mismatch: "+name)
    receipt[name]={"url":url,"sha256":actual,"size":file.stat().st_size}
(folder/"provenance.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
