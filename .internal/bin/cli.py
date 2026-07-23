#!/usr/bin/env python3
"""
Gallery CLI - Command-line interface for managing the project gallery system.

Available commands:
  create [name]              - Scaffold a new project folder with required structure
  update [name|all]          - Validate and sync info.json data
  remove [name]              - Safely delete a project folder
  serve                      - Generate gallery and start local http.server
  sync                       - Automate git add, commit, and push
  migrate [name] [new_repo]  - Clone project to another repo with renamed references
"""

import sys
import os
import json
import shutil
import subprocess
import uuid
import tempfile
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import time

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# Add parent directory to path to import gallery generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generative_galery import generator

# Constants
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PROJECTS_DIR = REPO_ROOT / "projects"
INTERNAL_DIR = REPO_ROOT / ".internal"

if load_dotenv is not None:
    load_dotenv(REPO_ROOT / ".env")


def get_github_credentials():
    """Load GitHub credentials from the environment."""
    return os.getenv("GITHUB_USERNAME"), os.getenv("GITHUB_PASSWORD")


def create_git_askpass_script(temp_dir):
    """Create a short-lived askpass helper for Git authentication."""
    helper_script = temp_dir / "git-askpass.py"
    helper_script.write_text(
        "#!/usr/bin/env python3\n"
        "import os\n"
        "import sys\n\n"
        "prompt = ' '.join(sys.argv[1:]).lower()\n"
        "if 'username' in prompt or 'login' in prompt:\n"
        "    sys.stdout.write(os.environ.get('GITHUB_USERNAME', ''))\n"
        "elif 'password' in prompt or 'token' in prompt:\n"
        "    sys.stdout.write(os.environ.get('GITHUB_PASSWORD', ''))\n",
        encoding="utf-8",
    )

    if os.name == "nt":
        script_path = temp_dir / "git-askpass.cmd"
        script_path.write_text(
            f'@echo off\r\n"{sys.executable}" "{helper_script}" %*\r\n',
            encoding="utf-8",
        )
        return script_path

    helper_script.chmod(0o700)
    return helper_script


def run_git_command(args, *, auth=False, capture_output=False, text=True, check=True, cwd=None):
    """Run a Git command with optional ephemeral authentication."""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"

    git_args = ["git"]

    if auth:
        username, password = get_github_credentials()
        if not username or not password:
            raise RuntimeError(
                "GITHUB_USERNAME and GITHUB_PASSWORD must be set in .env for authenticated Git operations"
            )

        env["GITHUB_USERNAME"] = username
        env["GITHUB_PASSWORD"] = password
        if os.name == "nt":
            env["GCM_INTERACTIVE"] = "never"

        git_args.extend(["-c", "credential.helper=", "-c", "credential.interactive=never"])

        with tempfile.TemporaryDirectory() as temp_dir:
            askpass_path = create_git_askpass_script(Path(temp_dir))
            env["GIT_ASKPASS"] = str(askpass_path)
            return subprocess.run(
                [*git_args, *args],
                capture_output=capture_output,
                text=text,
                check=check,
                env=env,
                cwd=cwd,
            )

    return subprocess.run(
        [*git_args, *args],
        capture_output=capture_output,
        text=text,
        check=check,
        env=env,
        cwd=cwd,
    )

def create_project(name):
    """Create a new project with the required folder structure."""
    if not name:
        print("Error: Project name is required")
        print("Usage: create [name]")
        return 1
    
    # Sanitize project name
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
    project_dir = PROJECTS_DIR / safe_name
    
    if project_dir.exists():
        print(f"Error: Project '{safe_name}' already exists")
        return 1
    
    print(f"Creating project '{safe_name}'...")
    
    # Create project structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / ".project_info").mkdir(exist_ok=True)
    (project_dir / ".project_info" / "images").mkdir(exist_ok=True)
    
    # Create default info.json
    info_data = {
        "id": str(uuid.uuid1()),
        "title": safe_name.replace("_", " ").title(),
        "desciption_short": f"A new {safe_name} project",
        "description_long": f"Detailed description for {safe_name}. Add more information here.",
        "icon_file_name": "icon.png",
        "images": [],
        "github_url": "None",
        "tags": ["New"],
        "date_published": datetime.now().strftime("%Y-%m-%d"),
        "version": "1.0.0"
    }
    
    info_path = project_dir / ".project_info" / "info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info_data, f, indent=4, ensure_ascii=False)
    
    # Create basic index.html
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{safe_name}</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>{safe_name.replace("_", " ").title()}</h1>
        <p>Your project content goes here.</p>
        <a href="../../index.html" class="back-link">← Back to Gallery</a>
    </div>
    <script src="script.js"></script>
</body>
</html>
"""
    
    with open(project_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    # Create basic style.css
    css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
}

.container {
    background: white;
    padding: 40px;
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
    max-width: 800px;
    width: 100%;
}

.back-link {
    display: inline-block;
    margin-top: 20px;
    padding: 10px 20px;
    background: #667eea;
    color: white;
    text-decoration: none;
    border-radius: 5px;
    transition: background 0.3s;
}

.back-link:hover {
    background: #764ba2;
}
"""
    
    with open(project_dir / "style.css", "w", encoding="utf-8") as f:
        f.write(css_content)
    
    # Create basic script.js
    js_content = """// Add your JavaScript code here
console.log('Project loaded successfully!');
"""
    
    with open(project_dir / "script.js", "w", encoding="utf-8") as f:
        f.write(js_content)
    
    print(f"✓ Project '{safe_name}' created successfully!")
    print(f"  Location: {project_dir}")
    print(f"  Add images to: {project_dir}/.project_info/images/")
    print(f"  Edit info at: {project_dir}/.project_info/info.json")
    
    return 0

def update_project(name):
    """Validate and sync project info.json data."""
    if not name:
        print("Error: Project name is required")
        print("Usage: update [name|all]")
        return 1
    
    if name.lower() == "all":
        # Update all projects
        if not PROJECTS_DIR.exists():
            print("Error: Projects directory not found")
            return 1
        
        projects = [p for p in PROJECTS_DIR.iterdir() if p.is_dir()]
        if not projects:
            print("No projects found")
            return 0
        
        print(f"Updating {len(projects)} project(s)...")
        success_count = 0
        
        for project_dir in projects:
            if validate_and_sync_project(project_dir):
                success_count += 1
        
        print(f"✓ Updated {success_count}/{len(projects)} project(s)")
        return 0 if success_count == len(projects) else 1
    
    else:
        # Update single project
        project_dir = PROJECTS_DIR / name
        if not project_dir.exists():
            print(f"Error: Project '{name}' not found")
            return 1
        
        if validate_and_sync_project(project_dir):
            print(f"✓ Project '{name}' updated successfully")
            return 0
        else:
            print(f"✗ Failed to update project '{name}'")
            return 1

def validate_and_sync_project(project_dir):
    """Validate and sync a single project's info.json."""
    info_path = project_dir / ".project_info" / "info.json"
    
    if not info_path.exists():
        print(f"  Warning: {project_dir.name} - info.json not found, creating default...")
        return create_default_info(project_dir)
    
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        # Validate required fields
        required_fields = ["id", "title", "desciption_short", "description_long", 
                          "icon_file_name", "images", "tags", "date_published", "version"]
        
        updated = False
        for field in required_fields:
            if field not in info:
                print(f"  Warning: {project_dir.name} - missing field '{field}', adding default...")
                info[field] = get_default_field_value(field, project_dir.name)
                updated = True
        
        # Ensure id is unique
        if not info.get("id") or len(info["id"]) < 10:
            info["id"] = str(uuid.uuid1())
            updated = True
        
        # Validate images exist
        images_dir = project_dir / ".project_info" / "images"
        if images_dir.exists():
            actual_images = [f.name for f in images_dir.iterdir() if f.is_file()]
            if set(info.get("images", [])) != set(actual_images):
                info["images"] = actual_images
                updated = True
                print(f"  Info: {project_dir.name} - synced images list")
        
        if updated:
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, indent=4, ensure_ascii=False)
            print(f"  ✓ {project_dir.name} - validated and synced")
        else:
            print(f"  ✓ {project_dir.name} - already valid")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  Error: {project_dir.name} - invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  Error: {project_dir.name} - {e}")
        return False

def create_default_info(project_dir):
    """Create default info.json for a project."""
    info_dir = project_dir / ".project_info"
    info_dir.mkdir(exist_ok=True)
    (info_dir / "images").mkdir(exist_ok=True)
    
    info_data = {
        "id": str(uuid.uuid1()),
        "title": project_dir.name.replace("_", " ").title(),
        "desciption_short": f"A {project_dir.name} project",
        "description_long": f"Detailed description for {project_dir.name}.",
        "icon_file_name": "icon.png",
        "images": [],
        "github_url": "None",
        "tags": ["Uncategorized"],
        "date_published": datetime.now().strftime("%Y-%m-%d"),
        "version": "1.0.0"
    }
    
    info_path = info_dir / "info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info_data, f, indent=4, ensure_ascii=False)
    
    return True

def get_default_field_value(field, project_name):
    """Get default value for a missing field."""
    defaults = {
        "id": str(uuid.uuid1()),
        "title": project_name.replace("_", " ").title(),
        "desciption_short": f"A {project_name} project",
        "description_long": f"Detailed description for {project_name}.",
        "icon_file_name": "icon.png",
        "images": [],
        "github_url": "None",
        "tags": ["Uncategorized"],
        "date_published": datetime.now().strftime("%Y-%m-%d"),
        "version": "1.0.0"
    }
    return defaults.get(field, "")

def remove_project(name):
    """Safely delete a project folder."""
    if not name:
        print("Error: Project name is required")
        print("Usage: remove [name]")
        return 1
    
    project_dir = PROJECTS_DIR / name
    
    if not project_dir.exists():
        print(f"Error: Project '{name}' not found")
        return 1
    
    # Confirm deletion
    print(f"Warning: This will permanently delete the project '{name}'")
    print(f"Location: {project_dir}")
    response = input("Type 'yes' to confirm: ")
    
    if response.lower() != "yes":
        print("Deletion cancelled")
        return 0
    
    try:
        shutil.rmtree(project_dir)
        print(f"✓ Project '{name}' removed successfully")
        return 0
    except Exception as e:
        print(f"Error: Failed to remove project - {e}")
        return 1

def serve_gallery():
    """Generate the gallery and start local http.server."""
    print("Generating gallery...")
    
    try:
        # Generate gallery
        generator.generate_gallery()
        print("✓ Gallery generated successfully")
        
        # Start server
        os.chdir(REPO_ROOT)
        port = 8000
        
        print(f"\nStarting server at http://localhost:{port}")
        print("Press Ctrl+C to stop the server\n")
        
        # Open browser after a short delay
        def open_browser():
            time.sleep(1)
            webbrowser.open(f"http://localhost:{port}")
        
        import threading
        threading.Thread(target=open_browser, daemon=True).start()
        
        # Start server
        handler = SimpleHTTPRequestHandler
        with HTTPServer(("", port), handler) as httpd:
            httpd.serve_forever()
        
        return 0
        
    except KeyboardInterrupt:
        print("\n\nServer stopped")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def sync_git():
    """Automate git add, commit, and push."""
    os.chdir(REPO_ROOT)
    
    try:
        # Check if git repo
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error: Not a git repository")
            return 1
        
        # Check for changes
        result = subprocess.run(["git", "status", "--porcelain"], 
                              capture_output=True, text=True)
        
        if not result.stdout.strip():
            print("No changes to commit")
            return 0
        
        print("Changes detected:")
        print(result.stdout)
        
        # Get commit message
        message = input("Enter commit message (or press Enter for auto-message): ").strip()
        if not message:
            message = f"Update gallery - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Git add
        print("\nAdding files...")
        subprocess.run(["git", "add", "."], check=True)
        
        # Git commit
        print("Committing changes...")
        subprocess.run(["git", "commit", "-m", message], check=True)
        
        # Git push
        print("Pushing to remote...")
        result = run_git_command(["push"], auth=True, capture_output=True)
        
        if result.returncode == 0:
            print("✓ Changes synced successfully")
            return 0
        else:
            print(f"Warning: Push failed - {result.stderr}")
            print("Changes committed locally but not pushed")
            return 1
        
    except subprocess.CalledProcessError as e:
        print(f"Error: Git command failed - {e}")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        return 1

def migrate_project(name, new_repo_url):
    """Clone a project to another repo with renamed references."""
    if not name or not new_repo_url:
        print("Error: Project name and new repo URL are required")
        print("Usage: migrate [name] [new_repo_url]")
        return 1
    
    project_dir = PROJECTS_DIR / name
    
    if not project_dir.exists():
        print(f"Error: Project '{name}' not found")
        return 1
    
    print(f"Migrating project '{name}' to {new_repo_url}...")
    
    # Create temporary directory
    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / name
        
        try:
            # Copy project to temp directory
            shutil.copytree(project_dir, temp_path)
            
            # Remove .project_info as it's gallery-specific
            info_dir = temp_path / ".project_info"
            if info_dir.exists():
                shutil.rmtree(info_dir)
            
            # Update references in HTML files
            for html_file in temp_path.glob("*.html"):
                content = html_file.read_text(encoding="utf-8")
                # Remove gallery back link
                content = content.replace('href="../../index.html"', 'href="#"')
                content = content.replace("← Back to Gallery", "")
                html_file.write_text(content, encoding="utf-8")
            
            # Initialize git and push
            os.chdir(temp_path)
            subprocess.run(["git", "init"], check=True)
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
            subprocess.run(["git", "branch", "-M", "main"], check=True)
            subprocess.run(["git", "remote", "add", "origin", new_repo_url], check=True)
            
            print("\nReady to push to new repository.")
            response = input("Push to remote? (yes/no): ")
            
            if response.lower() == "yes":
                run_git_command(["push", "-u", "origin", "main"], auth=True, check=True)
                print(f"✓ Project migrated successfully to {new_repo_url}")
            else:
                print(f"Project prepared in {temp_path}")
                print("You can manually push later")
            
            return 0
            
        except Exception as e:
            print(f"Error: Migration failed - {e}")
            return 1

def print_help():
    """Print help message."""
    print(__doc__)
    print("\nExamples:")
    print("  cli.py create my-new-project")
    print("  cli.py update all")
    print("  cli.py serve")
    print("  cli.py sync")
    print("  cli.py remove old-project")
    print("  cli.py migrate my-project https://github.com/user/new-repo.git")

def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_help()
        return 1
    
    command = sys.argv[1].lower()
    
    if command == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        return create_project(name)
    
    elif command == "update":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        return update_project(name)
    
    elif command == "remove":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        return remove_project(name)
    
    elif command == "serve":
        return serve_gallery()
    
    elif command == "sync":
        return sync_git()
    
    elif command == "migrate":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        new_repo = sys.argv[3] if len(sys.argv) > 3 else None
        return migrate_project(name, new_repo)
    
    elif command in ["help", "-h", "--help"]:
        print_help()
        return 0
    
    else:
        print(f"Error: Unknown command '{command}'")
        print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
