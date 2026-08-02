param(
    [string]$Apk = (
        Join-Path $PSScriptRoot `
            "..\android\artifacts\WarioWareTwisted-Android-private-S22-fix-arm64-debug.apk"
    ),
    [string]$OutputDirectory = (
        Join-Path $PSScriptRoot "..\android\artifacts\s22-device-validation"
    ),
    [int]$BootWaitSeconds = 25,
    [int]$GameWaitSeconds = 30
)

$ErrorActionPreference = "Stop"

$adb = (Get-Command adb -ErrorAction Stop).Source
$apkPath = (Resolve-Path -LiteralPath $Apk).Path
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null

$deviceLines = & $adb devices |
    Select-Object -Skip 1 |
    Where-Object { $_ -match "^(?<serial>\S+)\s+device$" }

$candidates = foreach ($line in $deviceLines) {
    if ($line -notmatch "^(?<serial>\S+)\s+device$") { continue }
    $serial = $Matches.serial
    if ($serial -like "emulator-*") { continue }
    $model = (& $adb -s $serial shell getprop ro.product.model).Trim()
    [pscustomobject]@{
        Serial = $serial
        Model = $model
    }
}

$phone = $candidates |
    Where-Object { $_.Model -match "^SM-S908" } |
    Select-Object -First 1

if (-not $phone) {
    $visible = if ($candidates) {
        ($candidates | ForEach-Object { "$($_.Model) [$($_.Serial)]" }) -join ", "
    }
    else {
        "none"
    }
    throw (
        "No authorized Galaxy S22 Ultra (SM-S908*) is visible to ADB. " +
        "Connected physical devices: $visible. Unlock the phone, enable USB " +
        "debugging, connect USB, and accept the computer authorization prompt."
    )
}

$serial = $phone.Serial
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$prefix = Join-Path $outputRoot "s22-$stamp"
$screenshotPath = "$prefix.png"
$runtimeLogPath = "$prefix-runtime.log"
$crashLogPath = "$prefix-crash.log"
$deviceInfoPath = "$prefix-device.txt"

@(
    "serial=$serial"
    "model=$($phone.Model)"
    "device=$((& $adb -s $serial shell getprop ro.product.device).Trim())"
    "soc=$((& $adb -s $serial shell getprop ro.soc.model).Trim())"
    "android=$((& $adb -s $serial shell getprop ro.build.version.release).Trim())"
    "sdk=$((& $adb -s $serial shell getprop ro.build.version.sdk).Trim())"
    "build=$((& $adb -s $serial shell getprop ro.build.fingerprint).Trim())"
) | Set-Content -LiteralPath $deviceInfoPath

Write-Host "Installing on $($phone.Model) [$serial]..."
& $adb -s $serial install -r $apkPath
if ($LASTEXITCODE -ne 0) { throw "adb install failed with exit code $LASTEXITCODE" }

& $adb -s $serial shell am force-stop com.mstan.wariowaretwisted
& $adb -s $serial logcat -c
& $adb -s $serial shell monkey `
    -p com.mstan.wariowaretwisted `
    -c android.intent.category.LAUNCHER 1 | Out-Host
if ($LASTEXITCODE -ne 0) { throw "Unable to launch WarioWare Twisted" }

Start-Sleep -Seconds $BootWaitSeconds

$sizeText = (& $adb -s $serial shell wm size) -join "`n"
$sizes = [regex]::Matches($sizeText, "(\d+)x(\d+)")
if ($sizes.Count -eq 0) { throw "Unable to determine the phone display size" }
$activeSize = $sizes[$sizes.Count - 1]
$naturalWidth = [int]$activeSize.Groups[1].Value
$naturalHeight = [int]$activeSize.Groups[2].Value
$landscapeWidth = [Math]::Max($naturalWidth, $naturalHeight)
$landscapeHeight = [Math]::Min($naturalWidth, $naturalHeight)
$aX = [int][Math]::Round($landscapeWidth * 0.90)
$aY = [int][Math]::Round($landscapeHeight * 0.62)

# Hold the on-screen A button long enough to be sampled even on a cold launch.
& $adb -s $serial shell input swipe $aX $aY $aX $aY 2500
Start-Sleep -Seconds $GameWaitSeconds

$remoteScreenshot = "/sdcard/warioware-s22-validation.png"
& $adb -s $serial shell screencap -p $remoteScreenshot
& $adb -s $serial pull $remoteScreenshot $screenshotPath | Out-Host
& $adb -s $serial shell rm $remoteScreenshot

(& $adb -s $serial shell run-as com.mstan.wariowaretwisted `
    cat files/android-runtime.log) |
    Set-Content -LiteralPath $runtimeLogPath
(& $adb -s $serial logcat -d -b crash) |
    Set-Content -LiteralPath $crashLogPath

$processId = (& $adb -s $serial shell pidof com.mstan.wariowaretwisted).Trim()
$activity = (& $adb -s $serial shell dumpsys activity activities) |
    Select-String -Pattern "topResumedActivity=.*com\.mstan\.wariowaretwisted" |
    Select-Object -First 1
$runtimeText = Get-Content -LiteralPath $runtimeLogPath -Raw
$crashText = Get-Content -LiteralPath $crashLogPath -Raw

$failures = [System.Collections.Generic.List[string]]::new()
if (-not $processId) {
    $failures.Add("the application process is not running")
}
if (-not $activity) {
    $failures.Add("WarioWareActivity is not the resumed foreground activity")
}
if ($runtimeText -notmatch "android: CPU backend=interpreter \(device-safe\)") {
    $failures.Add("the device-safe Android CPU backend was not confirmed")
}
if ($runtimeText -match "SELF-HEAL|missing static coverage") {
    $failures.Add("the runtime reported an unexpected static-dispatch miss")
}
if ($crashText -match "com\.mstan\.wariowaretwisted|libmain\.so") {
    $failures.Add("Android's crash buffer contains a WarioWare native crash")
}

if ($failures.Count -gt 0) {
    throw (
        "S22 validation failed: " + ($failures -join "; ") + ". Evidence: $prefix*"
    )
}

Write-Host "S22 validation passed."
Write-Host "Screenshot: $screenshotPath"
Write-Host "Runtime log: $runtimeLogPath"
Write-Host "Crash log: $crashLogPath"
Write-Host "Device info: $deviceInfoPath"
