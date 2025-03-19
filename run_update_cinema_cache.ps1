# PowerShell script to run the update_cinema_cache command with optimized parameters
# This script is designed to be run directly from PowerShell on Windows

# Set the current directory to the script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptPath

# Log file path
$logDir = Join-Path -Path $scriptPath -ChildPath "logs"
if (-not (Test-Path -Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir | Out-Null
}
$logFile = Join-Path -Path $logDir -ChildPath "update_cinema_cache_$(Get-Date -Format 'yyyyMMdd').log"

# Function to write to log file
function Write-Log {
    param (
        [string]$message
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Out-File -FilePath $logFile -Append
    Write-Host "$timestamp - $message"
}

# Start the update process
Write-Log "=== Cinema Cache Update Started at $(Get-Date) ==="

# Activate the virtual environment
Write-Log "Activating virtual environment..."
try {
    # Check if venv directory exists
    $venvPath = Join-Path -Path $scriptPath -ChildPath "venv"
    $venvActivate = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
    
    if (Test-Path -Path $venvActivate) {
        # Activate the virtual environment
        & $venvActivate
        Write-Log "Virtual environment activated successfully"
    } else {
        Write-Log "Virtual environment not found at $venvPath, using system Python"
    }
} catch {
    Write-Log "Error activating virtual environment: $_"
    Write-Log "Continuing with system Python..."
}

# First run the update_release_status command
Write-Log "Running update_release_status command..."
try {
    $output = python manage.py update_release_status --days=7 --batch-size=50 --use_parallel
    foreach ($line in $output) {
        Write-Log $line
    }
    Write-Log "update_release_status command completed successfully"
} catch {
    Write-Log "Error running update_release_status: $_"
    Write-Log "Continuing with update_movie_cache..."
}

# Run the update_movie_cache command with optimized parameters
Write-Log "Running update_movie_cache command with optimized parameters..."
try {
    $output = python manage.py update_movie_cache --force --max-pages=0 --batch-size=15 --batch-delay=1 --time-window-months=6 --prioritize-flags --use_parallel
    foreach ($line in $output) {
        Write-Log $line
    }
    Write-Log "update_movie_cache command completed successfully"
} catch {
    Write-Log "Error running update_movie_cache: $_"
    Write-Log "Cache update failed"
    Write-Log "=== Cinema Cache Update Finished with Errors at $(Get-Date) ==="
    exit 1
}

# End the log
Write-Log "=== Cinema Cache Update Finished Successfully at $(Get-Date) ==="

# Keep only the last 7 log files
$oldLogs = Get-ChildItem -Path $logDir -Filter "update_cinema_cache_*.log" | 
           Sort-Object LastWriteTime -Descending | 
           Select-Object -Skip 7
foreach ($log in $oldLogs) {
    Remove-Item -Path $log.FullName
    Write-Log "Deleted old log file: $($log.Name)"
}

# Deactivate the virtual environment if it was activated
if (Test-Path -Path $venvActivate) {
    deactivate
    Write-Log "Virtual environment deactivated"
}

exit 0 