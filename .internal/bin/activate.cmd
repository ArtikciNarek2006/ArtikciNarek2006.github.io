@echo off
REM Gallery CLI Activation Script for Windows Command Prompt

REM Get script directory
set SCRIPT_DIR=%~dp0
set INTERNAL_DIR=%SCRIPT_DIR%..
set VENV_DIR=%INTERNAL_DIR%\venv

REM Check if virtual environment exists
if not exist "%VENV_DIR%" (
    echo Virtual environment not found. Creating...
    python -m venv "%VENV_DIR%"
    
    REM Activate and install dependencies
    call "%VENV_DIR%\Scripts\activate.bat"
    pip install -r "%INTERNAL_DIR%\requirements.txt"
    echo Virtual environment created successfully!
) else (
    call "%VENV_DIR%\Scripts\activate.bat"
)

REM Create gallery command alias
doskey gallery=python "%SCRIPT_DIR%cli.py" $*
doskey deactivate_gallery=call "%VENV_DIR%\Scripts\deactivate.bat" $T echo Gallery CLI deactivated

echo Gallery CLI activated!
echo Available commands:
echo   gallery create [name]              - Create a new project
echo   gallery update [name^|all]          - Update project info
echo   gallery remove [name]              - Remove a project
echo   gallery serve                      - Generate and serve gallery
echo   gallery sync                       - Git add, commit, and push
echo   gallery migrate [name] [repo_url]  - Migrate project to new repo
echo   deactivate_gallery                 - Deactivate and exit
echo.
echo Run 'gallery help' for more information
