<#
Build the WarioWareTwistedRecomp Windows x64 release zip.

Modeled on MinishCapRecomp/tools/make_release.ps1. The archive contains only
the stripped desktop executable, required runtime DLLs, recomp-ui assets,
the overlay toolchain, the validated warm overlay cache, the game
configuration, and a release README.
ROMs, BIOS images, saves, and Android APKs are explicitly rejected.

Usage:
  powershell -File tools\make_release.ps1 -Version 0.0.1
#>
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$BuildDir = 'build-release'
)

$ErrorActionPreference = 'Stop'
(Get-Process -Id $PID).PriorityClass = 'BelowNormal'

$MingwBin = 'C:\msys64\mingw64\bin'
$CMake = Join-Path $MingwBin 'cmake.exe'
$env:PATH = "$MingwBin;$env:PATH"

$Root = Split-Path -Parent $PSScriptRoot
$Build = Join-Path $Root $BuildDir
$Out = Join-Path $Root 'release-stage'
$Engine = Join-Path $Root 'gbarecomp'
$Ui = Join-Path $Root 'recomp-ui'
$Target = 'WarioWareTwistedRecomp'
$Dlls = @('SDL2.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll',
    'libwinpthread-1.dll')

if (-not (Test-Path (Join-Path $Engine 'CMakeLists.txt'))) {
    throw "gbarecomp submodule missing: $Engine"
}
if (-not (Test-Path (Join-Path $Ui 'recomp_ui.cmake'))) {
    throw "recomp-ui submodule missing: $Ui"
}

New-Item -ItemType Directory -Force $Out | Out-Null

& $CMake -S $Root -B $Build -G Ninja `
    -DCMAKE_C_COMPILER="$MingwBin/cc.exe" `
    -DCMAKE_CXX_COMPILER="$MingwBin/c++.exe" `
    -DCMAKE_MAKE_PROGRAM="$MingwBin/ninja.exe" `
    -DCMAKE_BUILD_TYPE=Release `
    "-DCMAKE_CXX_FLAGS_RELEASE=-O2 -DNDEBUG" `
    -DGBARECOMP_ROOT="$Engine" `
    -DGBARECOMP_RUNTIME_UI_ROOT="$Ui" `
    -DGBARECOMP_BUILD_ORACLE=OFF `
    -DGBARECOMP_MINGW_PREFIX_UNIX="/c/msys64/mingw64" `
    -DSDL2_INCLUDE_DIR="C:/msys64/mingw64/include/SDL2" `
    -DSDL2_LIBRARY="C:/msys64/mingw64/lib/libSDL2.dll.a"
if ($LASTEXITCODE -ne 0) {
    throw "configure failed ($LASTEXITCODE)"
}

& $CMake --build $Build --target $Target --parallel 2
if ($LASTEXITCODE -ne 0) {
    throw "build failed ($LASTEXITCODE)"
}

$Exe = Join-Path $Build "$Target.exe"
if (-not (Test-Path $Exe)) {
    throw "expected executable missing: $Exe"
}
& (Join-Path $MingwBin 'strip.exe') $Exe
if ($LASTEXITCODE -ne 0) {
    throw "strip failed ($LASTEXITCODE)"
}

$StageName = "$Target-windows-x64-v$Version"
$Stage = Join-Path $Out $StageName
$Zip = Join-Path $Out "$StageName.zip"

if (Test-Path $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
if (Test-Path $Zip) {
    Remove-Item -LiteralPath $Zip -Force
}
New-Item -ItemType Directory -Force $Stage | Out-Null

Copy-Item -LiteralPath $Exe -Destination $Stage
foreach ($Dll in $Dlls) {
    Copy-Item -LiteralPath (Join-Path $MingwBin $Dll) -Destination $Stage
}

$Assets = Join-Path $Build 'assets'
if (-not (Test-Path (Join-Path $Assets 'img'))) {
    throw "recomp-ui launcher assets missing: $Assets"
}
Copy-Item -LiteralPath $Assets -Destination $Stage -Recurse

$ConfigSource = Join-Path $Root 'variants\warioware_twisted\game.toml'
$ConfigStage = Join-Path $Stage 'variants\warioware_twisted'
New-Item -ItemType Directory -Force $ConfigStage | Out-Null
Copy-Item -LiteralPath $ConfigSource -Destination $ConfigStage

# WarioWare copies several routines to RAM during boot. Its cold self-heal
# route currently reaches an interpreter-only bridge that cannot reconstruct
# one of those routines, while the validated warm cache reaches attract mode.
# Ship DLLs only (never the ROM-derived C/log diagnostics) under both backend
# names: auto selects gcc on a developer box and bundled tcc on a player box.
$RomSha1 = 'f0102d0d6f7596fe853d5d0a94682718278e083a'
$WarmCacheSource = Join-Path $Root `
    "recomp_cache\$RomSha1\gcc\windows-x64\abi3-ram3"
$WarmDlls = @(Get-ChildItem -LiteralPath $WarmCacheSource `
    -Filter '*.dll' -File)
if ($WarmDlls.Count -lt 1) {
    throw "validated WarioWare warm overlay cache missing: $WarmCacheSource"
}
foreach ($Backend in @('gcc', 'tcc')) {
    $WarmCacheStage = Join-Path $Stage `
        "recomp_cache\$RomSha1\$Backend\windows-x64\abi3-ram3"
    New-Item -ItemType Directory -Force $WarmCacheStage | Out-Null
    Copy-Item -LiteralPath $WarmDlls.FullName -Destination $WarmCacheStage
}

& (Join-Path $Engine 'tools\fetch_tcc.ps1') `
    -Toolchain (Join-Path $Stage 'overlay_toolchain') `
    -EngineRoot $Engine
if ($LASTEXITCODE -ne 0) {
    throw "overlay toolchain staging failed ($LASTEXITCODE)"
}

@"
# WarioWare: Twisted! - GBA static recompilation (Windows x64)

This is the desktop v$Version release. Keep the executable, four DLLs,
``assets``, ``overlay_toolchain``, ``recomp_cache``, and ``variants`` folders
together.

Run ``WarioWareTwistedRecomp.exe``. In the launcher, select your own
legally-obtained WarioWare: Twisted! (USA) ROM and GBA BIOS, then press PLAY.
Neither file is included in this archive.

Expected ROM SHA-1:
``f0102d0d6f7596fe853d5d0a94682718278e083a``

Motion controls:

- A DualSense or other SDL controller motion sensor can drive the cartridge
  gyro. Adjust it under Controller > Configure > Motion.
- Hold the left mouse button and drag horizontally for simulated gyro.

The Android prototype is experimental and is not included in this release.
"@ | Out-File -LiteralPath (Join-Path $Stage 'README.md') -Encoding utf8

$ForbiddenExtensions = @('.gba', '.agb', '.bin', '.apk', '.sav', '.srm')
$Forbidden = Get-ChildItem -LiteralPath $Stage -Recurse -File |
    Where-Object { $ForbiddenExtensions -contains $_.Extension.ToLowerInvariant() }
if ($Forbidden) {
    $Names = ($Forbidden.FullName -join [Environment]::NewLine)
    throw "release staging contains forbidden ROM/BIOS/APK/save files:`n$Names"
}

Compress-Archive -Path (Join-Path $Stage '*') -DestinationPath $Zip
Write-Host "Created desktop release archive:"
Get-Item -LiteralPath $Zip | Format-List FullName, Length, LastWriteTime
