$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

if (-not (Test-Path ".venv")) {
    py -3 -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt

$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $Root "pw-browsers"
& .\.venv\Scripts\python.exe -m playwright install chromium

& .\.venv\Scripts\pyinstaller.exe `
    --noconfirm `
    --clean `
    --onedir `
    --console `
    --name WXLiveSpy `
    --collect-all playwright `
    wx_live_spy.py

Copy-Item -Recurse -Force "pw-browsers" "dist\WXLiveSpy\pw-browsers"

$Iscc = Get-Command iscc.exe -ErrorAction SilentlyContinue
$IsccPath = if ($Iscc) { $Iscc.Source } else { "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" }
if (Test-Path $IsccPath) {
    & $IsccPath "installer\WXLiveSpy.iss"
    Write-Host "Installer created in installer\Output"
} else {
    Write-Host "Inno Setup not found; portable build created in dist\WXLiveSpy"
}
