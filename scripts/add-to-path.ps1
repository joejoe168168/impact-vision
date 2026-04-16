# Add impact-vision to PATH (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\add-to-path.ps1

$scriptsDir = python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null

if (-not $scriptsDir) {
    Write-Host "Error: Python not found. Install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($currentPath -like "*$scriptsDir*") {
    Write-Host "Already on PATH: $scriptsDir" -ForegroundColor Green
} else {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$scriptsDir", "User")
    $env:Path = "$env:Path;$scriptsDir"
    Write-Host "Added to PATH: $scriptsDir" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Yellow
Write-Host "IMPORTANT: You must RESTART your terminal (close and reopen" -ForegroundColor Yellow
Write-Host "PowerShell) for the PATH change to take effect." -ForegroundColor Yellow
Write-Host "After restarting, run: impact-vision --help" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow
