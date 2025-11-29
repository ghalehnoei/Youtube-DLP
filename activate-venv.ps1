# Manual virtual environment activation for PowerShell
# This bypasses certificate validation issues by manually setting up the environment

$ErrorActionPreference = "Stop"

# Get the directory where this script is located
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$venvPath = Join-Path $scriptDir "venv"

if (-not (Test-Path $venvPath)) {
    Write-Error "Virtual environment not found at: $venvPath"
    return
}

# Save old environment variables
if (Test-Path env:VIRTUAL_ENV) {
    $env:_OLD_VIRTUAL_ENV = $env:VIRTUAL_ENV
}

# Set virtual environment
$env:VIRTUAL_ENV = $venvPath

# Save old PATH
if (Test-Path env:PATH) {
    $env:_OLD_VIRTUAL_PATH = $env:PATH
}

# Prepend venv Scripts to PATH
$env:PATH = "$venvPath\Scripts;$env:PATH"

# Clear PYTHONHOME if set
if (Test-Path env:PYTHONHOME) {
    $env:_OLD_VIRTUAL_PYTHONHOME = $env:PYTHONHOME
    Remove-Item env:PYTHONHOME
}

# Set prompt
$env:VIRTUAL_ENV_PROMPT = Split-Path -Leaf $venvPath

# Update PowerShell prompt function
function global:prompt {
    $prompt = "($env:VIRTUAL_ENV_PROMPT) "
    $prompt += $ExecutionContext.SessionState.Path.CurrentLocation
    $prompt += "> "
    return $prompt
}

Write-Host "Virtual environment activated: $venvPath" -ForegroundColor Green

