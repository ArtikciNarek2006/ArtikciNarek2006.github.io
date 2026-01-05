# Gallery CLI Activation Script for PowerShell

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InternalDir = Split-Path -Parent $ScriptDir
$VenvDir = Join-Path $InternalDir "venv"

# Check if virtual environment exists
if (-not (Test-Path $VenvDir)) {
    Write-Host "Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv $VenvDir
    
    # Activate and install dependencies
    & "$VenvDir\Scripts\Activate.ps1"
    pip install --upgrade pip
    pip install -r "$InternalDir\requirements.txt"
    Write-Host "Virtual environment created successfully!" -ForegroundColor Green
} else {
    & "$VenvDir\Scripts\Activate.ps1"
}

# Create gallery command function
function gallery {
    python "$ScriptDir\cli.py" $args
}

# Create deactivate function
function deactivate_gallery {
    deactivate
    Remove-Item Function:\gallery
    Remove-Item Function:\deactivate_gallery
    Write-Host "Gallery CLI deactivated" -ForegroundColor Green
}

Write-Host "Gallery CLI activated!" -ForegroundColor Green
Write-Host "Available commands:"
Write-Host "  gallery create [name]              - Create a new project"
Write-Host "  gallery update [name|all]          - Update project info"
Write-Host "  gallery remove [name]              - Remove a project"
Write-Host "  gallery serve                      - Generate and serve gallery"
Write-Host "  gallery sync                       - Git add, commit, and push"
Write-Host "  gallery migrate [name] [repo_url]  - Migrate project to new repo"
Write-Host "  deactivate_gallery                 - Deactivate and exit"
Write-Host ""
Write-Host "Run 'gallery help' for more information"
