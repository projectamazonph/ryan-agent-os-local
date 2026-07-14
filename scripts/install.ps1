$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$InstallRoot = if ($env:RAO_INSTALL_ROOT) { $env:RAO_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "RyanAgentOS" }
$BinDir = if ($env:RAO_BIN_DIR) { $env:RAO_BIN_DIR } else { Join-Path $InstallRoot "bin" }
$AppDir = Join-Path $InstallRoot "app"

$Python = Get-Command py -ErrorAction SilentlyContinue
if (-not $Python) {
    throw "Python 3.11 or newer is required."
}

& py -3.11 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"
New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
if (Test-Path $AppDir) { Remove-Item -Recurse -Force $AppDir }
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null
Copy-Item -Recurse -Force (Join-Path $ProjectRoot "src") (Join-Path $AppDir "src")

$Launcher = Join-Path $BinDir "rao.cmd"
$SourcePath = Join-Path $AppDir "src"
"@echo off`r`nset RAO_EXECUTABLE=$Launcher`r`nset PYTHONPATH=$SourcePath;%PYTHONPATH%`r`npy -3.11 -m rao.cli %*`r`n" | Set-Content -Encoding ASCII $Launcher
& $Launcher init
Write-Host "Installed: $Launcher"

$currentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if (-not (($currentUserPath -split ";") -contains $BinDir)) {
    $prefix = if ($currentUserPath) { $currentUserPath.TrimEnd(";") + ";" } else { "" }
    [Environment]::SetEnvironmentVariable("Path", ($prefix + $BinDir), "User")
    Write-Host "Added $BinDir to the user PATH. Open a new terminal before using rao."
}
