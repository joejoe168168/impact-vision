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
Write-Host "Verifying..." -ForegroundColor Cyan
$ivPath = Get-Command impact-vision -ErrorAction SilentlyContinue
if ($ivPath) {
    Write-Host "impact-vision is ready! Try: impact-vision --help" -ForegroundColor Green
} else {
    Write-Host "Please restart your terminal, then run: impact-vision --help" -ForegroundColor Yellow
}
