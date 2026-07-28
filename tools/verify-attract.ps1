param(
    [string]$OutputDirectory = (
        Join-Path $PSScriptRoot "..\build\attract-verify"
    ),
    [string]$ExpectedSha256 = (
        "1092560B258A080030223DC904559253028DC1C2B5BA01D4AF589874C8CC8D15"
    ),
    [switch]$Interpreter,
    [switch]$ColdCache,
    [int]$Frames = 3000
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$exe = Join-Path $projectRoot "build\WarioWareTwistedRecomp.exe"
$config = Join-Path $projectRoot `
    "variants\warioware_twisted\game.toml"
$inputTrace = Join-Path $projectRoot "tests\attract-input.csv"

if (-not (Test-Path -LiteralPath $exe)) {
    throw "Missing $exe. Configure and build WarioWareTwistedRecomp first."
}

$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$framePath = Join-Path $outputRoot "attract-frame-$Frames.png"
$logPath = Join-Path $outputRoot "attract-frame-$Frames.log"
$savePath = Join-Path $outputRoot (
    "attract-" + [System.Guid]::NewGuid().ToString("N") + ".sav"
)

$savedReplay = $env:GBARECOMP_INPUT_REPLAY
$savedGyro = $env:GBARECOMP_GYRO_TEST
$savedWatchdog = $env:GBARECOMP_HANG_WATCHDOG
$savedForceInterp = $env:GBARECOMP_FORCE_INTERP
$savedHealCache = $env:GBARECOMP_HEAL_CACHE

try {
    $env:GBARECOMP_INPUT_REPLAY = $inputTrace
    # The cartridge explicitly calibrates during startup. Keep it centered;
    # an always-moving sweep correctly prevents calibration from completing.
    $env:GBARECOMP_GYRO_TEST = "0"
    $env:GBARECOMP_HANG_WATCHDOG = "0"
    $backend = "static"
    $env:GBARECOMP_FORCE_INTERP = "0"
    if ($Interpreter) {
        $backend = "interpreter"
        $env:GBARECOMP_FORCE_INTERP = "1"
    }
    $cacheMode = "warm"
    if ($ColdCache) {
        $cacheMode = "cold"
        $env:GBARECOMP_HEAL_CACHE = Join-Path $outputRoot (
            "heal-cache-" + [System.Guid]::NewGuid().ToString("N")
        )
    }

    # The runtime intentionally reports non-fatal static coverage/self-heal
    # status on stderr. Capture it without letting PowerShell promote the line
    # to a terminating NativeCommandError; the native exit code remains the
    # authoritative failure signal.
    $savedErrorAction = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $runOutput = & $exe `
            --config $config `
            --bios-hle `
            --no-window `
            --save-path $savePath `
            --frames $Frames `
            --dump-png $framePath 2>&1
        $runExit = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $savedErrorAction
    }
    $runText = $runOutput | ForEach-Object {
        if ($_ -is [System.Management.Automation.ErrorRecord]) {
            $_.Exception.Message
        }
        else {
            [string]$_
        }
    }
    $runText | Set-Content -LiteralPath $logPath
    $runText | Write-Output

    if ($runExit -ne 0) {
        throw "Attract run failed with exit code $runExit. See $logPath"
    }

    $summary = $runText -join "`n"
    if ($summary -notmatch "unmapped=0 io_unhandled=0" -or
        $summary -notmatch "ppu_frames=$Frames") {
        throw "Attract run did not meet the runtime counter gate. See $logPath"
    }

    $actualSha256 = (Get-FileHash -LiteralPath $framePath `
        -Algorithm SHA256).Hash
    if ($ExpectedSha256 -and $actualSha256 -ne $ExpectedSha256) {
        throw (
            "Attract framebuffer hash mismatch.`n" +
            "Expected: $ExpectedSha256`n" +
            "Actual:   $actualSha256`n" +
            "Frame:    $framePath"
        )
    }

    Write-Output "attract_verify=PASS"
    Write-Output "backend=$backend"
    Write-Output "heal_cache=$cacheMode"
    Write-Output "frame=$framePath"
    Write-Output "sha256=$actualSha256"
}
finally {
    if (Test-Path -LiteralPath $savePath) {
        Remove-Item -LiteralPath $savePath -Force
    }
    $env:GBARECOMP_INPUT_REPLAY = $savedReplay
    $env:GBARECOMP_GYRO_TEST = $savedGyro
    $env:GBARECOMP_HANG_WATCHDOG = $savedWatchdog
    $env:GBARECOMP_FORCE_INTERP = $savedForceInterp
    $env:GBARECOMP_HEAL_CACHE = $savedHealCache
}
