param([string]$Python='python',[string]$BuildRoot='',[string]$Uv='uv',[string]$Environment='')
$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
if(!$BuildRoot){$BuildRoot=Join-Path $repo 'dist/workspace-build'}
New-Item -ItemType Directory -Force $BuildRoot,(Join-Path $repo 'dist') | Out-Null
$source=Join-Path $BuildRoot 'server';$client=Join-Path $BuildRoot 'webclient-3.0.0'
robocopy $repo $source /E /XD .git dist build node_modules *.egg-info __pycache__ .pytest_cache /NFL /NDL /NJH /NJS /NP | Out-Null
if($LASTEXITCODE -ge 8){throw 'Source staging failed'}
$archive=Join-Path $BuildRoot 'webclient.zip'
if(!(Test-Path $archive)){Invoke-WebRequest 'https://github.com/swingmx/webclient/archive/refs/tags/v3.0.0.zip' -OutFile $archive}
if((Get-FileHash $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne '75a3dbfd5a3c3f52ab10046197e9766ff370adbb369e3e35a14a434cf0e5d7b9'){throw 'Webclient checksum mismatch'}
Expand-Archive -LiteralPath $archive -DestinationPath $BuildRoot -Force
& $Python (Join-Path $repo 'scripts/patch-workspace-client.py') $client
if($LASTEXITCODE){throw 'Webclient adapter failed'}
Copy-Item (Join-Path $repo 'scripts/workspace-client-package-lock.json') (Join-Path $client 'package-lock.json')
Push-Location $client
try {npm.cmd ci --no-audit --no-fund;if($LASTEXITCODE){throw 'Client install failed'};npm.cmd run build;if($LASTEXITCODE){throw 'Client build failed'}} finally{Pop-Location}
# Retain the upstream advanced settings in a separate entry, at the same mounted
# path so its authenticated API/audio/worker URLs keep their existing contract.
Push-Location (Join-Path $repo 'web')
try {npm.cmd ci --no-audit --no-fund;if($LASTEXITCODE){throw 'Listening client install failed'};npm.cmd run build;if($LASTEXITCODE){throw 'Listening client build failed'}} finally{Pop-Location}
$venv=if($Environment){$Environment}else{Join-Path $BuildRoot 'venv'}; if(!(Test-Path (Join-Path $venv 'Scripts/python.exe'))){ & $Uv venv --python $Python $venv }
if($LASTEXITCODE){throw 'Build environment failed'}
$py=Join-Path $venv 'Scripts/python.exe'
& $Uv pip install --python $py --no-deps -r (Join-Path $repo 'requirements.txt')
if($LASTEXITCODE){throw 'Runtime dependency install failed'}
& $Uv pip install --python $py 'Authlib==1.6.5' 'pyinstaller==6.22.3' 'imageio-ffmpeg==0.6.0' setuptools setuptools-scm
if($LASTEXITCODE){throw 'Build dependency install failed'}
$env:SETUPTOOLS_SCM_PRETEND_VERSION='3.0.1'
& $Uv pip install --python $py --no-deps -e $source
if($LASTEXITCODE){throw 'Server install failed'}
$merged=Join-Path $BuildRoot ('client-'+[guid]::NewGuid().ToString('N'))
& $py (Join-Path $repo 'scripts/package-client.py') --classic (Join-Path $client 'dist') --listening (Join-Path $repo 'web/dist') --output $merged --zip (Join-Path $source 'client.zip')
if($LASTEXITCODE){throw 'Client bundling failed'}
$env:SWING_SERVER_STAGE=$source
@'
import os, shutil
from pathlib import Path
import imageio_ffmpeg
stage=Path(os.environ['SWING_SERVER_STAGE'])
shutil.copyfile(imageio_ffmpeg.get_ffmpeg_exe(),stage/'ffmpeg.exe')
'@ | & $py -
if($LASTEXITCODE){throw 'Client bundling failed'}
$env:WORKSPACE_FFMPEG=Join-Path $source 'ffmpeg.exe';$env:PYTHONPATH=Join-Path $source 'src'
Push-Location $source
try {& $py -m PyInstaller --noconfirm --clean workspace.spec;if($LASTEXITCODE){throw 'Music packaging failed'}}finally{Pop-Location}
Copy-Item (Join-Path $source 'dist/Music.exe') (Join-Path $repo 'dist/Music.exe')
Get-FileHash (Join-Path $repo 'dist/Music.exe') -Algorithm SHA256
