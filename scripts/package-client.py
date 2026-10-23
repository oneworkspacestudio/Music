"""Merge advanced settings and the listening UI without stale gzip/HTML caches."""
import argparse
import gzip
from pathlib import Path
import shutil
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--classic", type=Path, required=True)
parser.add_argument("--listening", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--zip", type=Path, required=True)
args = parser.parse_args()
if args.output.exists():
    raise ValueError("Use a new merge directory")
args.output.mkdir(parents=True)
for source in (args.classic, args.listening):
    for file in source.rglob("*"):
        if not file.is_file() or file.suffix == ".gz":
            continue
        # Upstream's Apple system fonts are not redistributed. Advanced settings
        # use ordinary browser system fonts instead.
        if file.suffix == ".woff2" and (file.name.startswith("SF") or file.name.startswith("sf-mono")):
            continue
        relative = file.relative_to(source)
        if source == args.classic and relative.as_posix() == "index.html":
            relative = Path("classic.html")
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, target)
classic = args.output / "classic.html"
classic.write_text(classic.read_text(encoding="utf-8").replace("</head>", "<style>*{font-family:Arial,Helvetica,sans-serif!important}</style></head>"), encoding="utf-8")
(args.output / "version.txt").write_text("3.0.1", encoding="utf-8")
for file in list(args.output.rglob("*")):
    if file.is_file() and file.suffix in (".js", ".css"):
        Path(str(file) + ".gz").write_bytes(gzip.compress(file.read_bytes(), mtime=0))
with zipfile.ZipFile(args.zip, "w", zipfile.ZIP_DEFLATED) as archive:
    for file in args.output.rglob("*"):
        if file.is_file():
            archive.write(file, "client/" + file.relative_to(args.output).as_posix())
print("Packaged listening UI and original advanced settings")
