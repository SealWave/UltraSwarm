param(
    [int]$Port = 9222,
    [string]$ChromePath = $env:BROWSER_USE_CHROME_PATH
)

$ErrorActionPreference = "Stop"

function Get-ChromePath {
    if ($ChromePath -and (Test-Path $ChromePath)) {
        return $ChromePath
    }

    $candidates = @(
        "$env:LOCALAPPDATA\ms-playwright\chromium-1223\chrome-win64\chrome.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    throw "Chrome executable not found. Set BROWSER_USE_CHROME_PATH or install Chrome."
}

$resolvedChrome = Get-ChromePath
$userDataDir = Join-Path $env:TEMP "ecom-browser-use-cdp"
New-Item -ItemType Directory -Force -Path $userDataDir | Out-Null

$env:BROWSER_USE_CDP_URL = "http://127.0.0.1:$Port"
$env:BROWSER_HEADLESS = "false"

$args = @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$userDataDir",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-popup-blocking",
    "--new-window",
    "about:blank"
)

Start-Process -FilePath $resolvedChrome -ArgumentList $args -WindowStyle Hidden

Write-Host "Chrome launched for browser-use."
Write-Host "CDP URL: $env:BROWSER_USE_CDP_URL"
Write-Host "User data dir: $userDataDir"
