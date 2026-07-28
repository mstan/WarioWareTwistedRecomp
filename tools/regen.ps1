param(
    [string]$GbarecompRoot = (
        Join-Path $PSScriptRoot "..\..\gbarecomp-warioware-twisted"
    )
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$engineRoot = (Resolve-Path $GbarecompRoot).Path
$recompiler = @(
    (Join-Path $engineRoot "build-native\gba_recompile.exe"),
    (Join-Path $engineRoot "build\gba_recompile.exe")
) | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
$rom = Join-Path $projectRoot `
    "variants\warioware_twisted\roms\warioware_twisted_usa.gba"
$config = Join-Path $projectRoot `
    "variants\warioware_twisted\game.toml"
$output = Join-Path $projectRoot `
    "variants\warioware_twisted\generated"

if (-not $recompiler) {
    throw "Missing gba_recompile.exe. Build the engine's gba_recompile target first."
}
if (-not (Test-Path -LiteralPath $rom)) {
    throw "Missing user-provided ROM: $rom"
}

& $recompiler --rom $rom --config $config --out $output
if ($LASTEXITCODE -ne 0) {
    throw "gba_recompile failed with exit code $LASTEXITCODE"
}
