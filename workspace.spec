# Build after scripts/patch-workspace-client.py and the upstream Vite client build.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH)
ffmpeg = os.environ["WORKSPACE_FFMPEG"]
tools = Path(os.environ["WORKSPACE_MUSIC_IMPORT_TOOLS"])
for name in ('yt-dlp.exe', 'node.exe'):
    if not (tools/name).is_file():
        raise RuntimeError('Missing verified import tool: '+name)
datas = [(str(root / 'client.zip'), '.'), (str(root / 'version.txt'), '.')]
datas += collect_data_files('swingmusic') + collect_data_files('flask_openapi3') + copy_metadata('swingmusic')
a = Analysis([str(root / 'run.py')], pathex=[str(root/'src')], datas=datas,
             binaries=[(ffmpeg, '.'), (str(tools/'yt-dlp.exe'),'import-tools'), (str(tools/'node.exe'),'import-tools')], hiddenimports=collect_submodules('swingmusic'),
             excludes=['locust','nuitka','pytest','tkinter','matplotlib','pandas','IPython'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='Music', console=True, strip=False, upx=False,
          icon=str(root / 'src/swingmusic/assets/logo-fill.light.ico'))
