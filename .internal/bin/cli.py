#!/usr/bin/env python3
"""
Gallery CLI - Command-line interface for managing the project gallery system.

Available commands:
  create [name]              - Scaffold a new project folder with required structure
  update [name|all]          - Validate and sync info.json data
  remove [name]              - Safely delete a project folder
    generate | gen             - Generate the gallery index.html without serving it
  serve                      - Generate gallery and start local http.server
    sync [--force]             - Automate git add, commit, and push
  migrate [name] [new_repo]  - Clone project to another repo with renamed references
"""

import sys
import os
import json
import importlib
import shutil
import subprocess
import uuid
import tempfile
import socket
import re
from urllib.parse import quote, urlsplit, urlunsplit
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import webbrowser
import time

# Add parent directory to path to import gallery generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from generative_galery import generator

# Constants
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PROJECTS_DIR = REPO_ROOT / "projects"
INTERNAL_DIR = REPO_ROOT / ".internal"
MIGRATIONS_DIR = INTERNAL_DIR / "migrations"


def get_dotenv_module():
    """Import python-dotenv lazily when it is available."""
    try:
        return importlib.import_module("dotenv")
    except ImportError:
        return None


def get_github_credentials():
    """Load GitHub credentials from the environment."""
    dotenv_path = REPO_ROOT / ".env"

    dotenv_module = get_dotenv_module()

    if dotenv_module is not None:
        dotenv_module.load_dotenv(dotenv_path=str(dotenv_path), override=True)

    username = os.getenv("GITHUB_USERNAME")
    password = os.getenv("GITHUB_PASSWORD")

    if (not username or not password) and dotenv_module is not None and dotenv_path.exists():
        values = dotenv_module.dotenv_values(str(dotenv_path))
        username = username or values.get("GITHUB_USERNAME")
        password = password or values.get("GITHUB_PASSWORD")

    return username, password


def build_authenticated_remote_url(remote_url, username, password):
    """Return a temporary GitHub HTTPS remote URL with embedded credentials."""
    parsed = urlsplit(remote_url)

    if parsed.hostname and parsed.hostname.lower() in {"github.com", "www.github.com"}:
        if parsed.scheme == "https":
            netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.hostname}"
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"

            return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))

        if parsed.scheme == "ssh":
            https_path = parsed.path if parsed.path.startswith("/") else f"/{parsed.path}"
            netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.hostname}"
            if parsed.port:
                netloc = f"{netloc}:{parsed.port}"

            return urlunsplit(("https", netloc, https_path, parsed.query, parsed.fragment))

    scp_match = re.match(r"^(?:(?P<user>[^@]+)@)?(?P<host>[^:]+):(?P<path>.+)$", remote_url)
    if scp_match and scp_match.group("host").lower() in {"github.com", "www.github.com"}:
        https_path = "/" + scp_match.group("path").lstrip("/")
        netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{scp_match.group('host')}"
        return urlunsplit(("https", netloc, https_path, "", ""))

    if parsed.scheme != "https" or not parsed.hostname:
        return remote_url

    netloc = f"{quote(username, safe='')}:{quote(password, safe='')}@{parsed.hostname}"
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"

    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


def get_current_branch():
    """Return the currently checked-out branch name."""
    result = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=True)
    branch = result.stdout.strip()

    if not branch or branch == "HEAD":
        raise RuntimeError("Cannot sync from a detached HEAD state")

    return branch


def get_remote_branch_sha(auth_remote_url, branch_name):
    """Return the SHA for a remote branch, or None if it does not exist."""
    result = run_git_command(["ls-remote", auth_remote_url, f"refs/heads/{branch_name}"], capture_output=True, text=True, check=True)
    output = result.stdout.strip()

    if not output:
        return None

    return output.split()[0]


def get_remote_branch_sha_for_sync(remote_url, branch_name):
    """Return the remote branch SHA using unauthenticated access first, then .env credentials if available."""
    try:
        return get_remote_branch_sha(remote_url, branch_name)
    except Exception:
        username, password = get_github_credentials()
        if not username or not password:
            return None

        auth_remote_url = build_authenticated_remote_url(remote_url, username, password)
        try:
            return get_remote_branch_sha(auth_remote_url, branch_name)
        except Exception:
            return None


def get_branch_divergence(remote_sha):
    """Return (ahead_count, behind_count) for HEAD relative to a remote SHA."""
    if not remote_sha:
        result = subprocess.run(["git", "rev-list", "--count", "HEAD"], capture_output=True, text=True, check=True)
        ahead_count = int(result.stdout.strip() or "0")
        return ahead_count, 0

    ahead_result = subprocess.run(["git", "rev-list", "--count", f"{remote_sha}..HEAD"], capture_output=True, text=True, check=True)
    behind_result = subprocess.run(["git", "rev-list", "--count", f"HEAD..{remote_sha}"], capture_output=True, text=True, check=True)

    ahead_count = int(ahead_result.stdout.strip() or "0")
    behind_count = int(behind_result.stdout.strip() or "0")
    return ahead_count, behind_count


def build_sync_hint(branch_name, force):
    """Return a concise hint for push failures or branch conflicts."""
    if force:
        return (
            f"Hint: `gallery sync --force` will create a remote backup branch before overwriting origin/{branch_name}. "
            f"You can also try `git push --force-with-lease origin HEAD:refs/heads/{branch_name}` if you want to manage it manually."
        )

    return (
        f"Hint: Run `gallery sync --force` to create a backup branch and overwrite origin/{branch_name}, "
        f"or run `git pull --rebase origin {branch_name}` and retry `gallery sync`."
    )


def push_with_auth(remote_url, branch_name, force=False, backup_branch_name=None):
    """Push the current branch using a temporary authenticated remote URL."""
    refspec = f"HEAD:refs/heads/{branch_name}"
    if force:
        refspec = f"+{refspec}"

    if backup_branch_name:
        remote_sha = get_remote_branch_sha(remote_url, branch_name)
        if remote_sha:
            backup_result = run_git_command(
                ["push", remote_url, f"{remote_sha}:refs/heads/{backup_branch_name}"],
                capture_output=True,
                text=True,
                check=False,
            )

            if backup_result.returncode != 0:
                return backup_result, f"Failed to create remote backup branch '{backup_branch_name}'"

            print(f"Created remote backup branch '{backup_branch_name}'")

    return run_git_command(["push", remote_url, refspec], capture_output=True, text=True, check=False), None


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
            env["SSH_ASKPASS"] = str(askpass_path)
            env["SSH_ASKPASS_REQUIRE"] = "force"
            git_args.extend(["-c", f"core.askPass={askpass_path}"])
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

def generate_gallery_only():
    """Generate the gallery without starting a server."""
    print("Generating gallery...")

    try:
        generator.generate_gallery()
        print("✓ Gallery generated successfully")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

def find_available_port(start_port=8000, max_port=8100):
    """Return the first available TCP port at or above start_port."""
    for port in range(start_port, max_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("", port))
            except OSError:
                continue

            return port

    raise RuntimeError(f"No available port found in range {start_port}-{max_port}")

def serve_gallery():
    """Generate the gallery and start local http.server."""
    try:
        result = generate_gallery_only()
        if result != 0:
            return result
        
        # Start server
        os.chdir(REPO_ROOT)
        port = find_available_port(8000)
        
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

def sync_git(force=False):
    """Automate git add, commit, and push."""
    os.chdir(REPO_ROOT)
    
    try:
        # Check if git repo
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error: Not a git repository")
            return 1
        
        # Check for changes
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        working_tree_dirty = bool(result.stdout.strip())

        branch_name = get_current_branch()
        remote_result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True, check=True)
        remote_url = remote_result.stdout.strip()
        remote_sha = get_remote_branch_sha_for_sync(remote_url, branch_name)
        ahead_count, behind_count = get_branch_divergence(remote_sha)

        if ahead_count == 0 and behind_count > 0 and not force:
            print(f"Error: Local branch '{branch_name}' is behind 'origin/{branch_name}' by {behind_count} commit(s).")
            print(build_sync_hint(branch_name, force=False))
            return 1

        should_push = working_tree_dirty or ahead_count > 0 or force
        if not should_push:
            print("No changes to commit")
            return 0

        if working_tree_dirty:
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

        username, password = get_github_credentials()
        if not username or not password:
            raise RuntimeError("GITHUB_USERNAME and GITHUB_PASSWORD must be set in .env for authenticated Git operations")

        auth_remote_url = build_authenticated_remote_url(remote_url, username, password)

        if force:
            print("Force mode enabled: creating a remote backup before overwrite...")

        print("Pushing to remote...")
        backup_branch_name = f"backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}" if force else None
        result, backup_error = push_with_auth(auth_remote_url, branch_name, force=force, backup_branch_name=backup_branch_name)

        if backup_error:
            print(f"Error: {backup_error}")
            print(build_sync_hint(branch_name, force=True))
            return 1

        if result.returncode == 0:
            print("✓ Changes synced successfully")
            return 0

        stderr = (result.stderr or "").strip()
        print(f"Error: Git push failed - {stderr if stderr else 'unknown error'}")
        print(build_sync_hint(branch_name, force))
        print("Changes remain committed locally but were not pushed")
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
    
    MIGRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    export_name = f"{name}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    export_dir = MIGRATIONS_DIR / export_name

    if export_dir.exists():
        shutil.rmtree(export_dir)

    try:
        # Copy project to a persistent export directory
        shutil.copytree(project_dir, export_dir)

        # Remove .project_info as it's gallery-specific
        info_dir = export_dir / ".project_info"
        if info_dir.exists():
            shutil.rmtree(info_dir)

        # Update references in HTML files
        for html_file in export_dir.glob("*.html"):
            content = html_file.read_text(encoding="utf-8")
            # Remove gallery back link
            content = content.replace('href="../../index.html"', 'href="#"')
            content = content.replace("← Back to Gallery", "")
            html_file.write_text(content, encoding="utf-8")

        # Initialize git and stage initial content
        os.chdir(export_dir)
        subprocess.run(["git", "init"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True)
        subprocess.run(["git", "branch", "-M", "main"], check=True)
        subprocess.run(["git", "remote", "add", "origin", new_repo_url], check=True)

        print(f"\nReady to push to new repository from {export_dir}.")
        response = input("Push to remote? (yes/no): ")

        if response.lower() == "yes":
            username, password = get_github_credentials()
            if not username or not password:
                raise RuntimeError("GITHUB_USERNAME and GITHUB_PASSWORD must be set in .env for authenticated Git operations")

            auth_remote_url = build_authenticated_remote_url(new_repo_url, username, password)
            run_git_command(["push", auth_remote_url, "main"], check=True, cwd=export_dir)
            print(f"✓ Project migrated successfully to {new_repo_url}")
        else:
            print(f"Project prepared in {export_dir}")
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
    print("  cli.py generate")
    print("  cli.py gen")
    print("  cli.py serve")
    print("  cli.py sync")
    print("  cli.py sync --force")
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
    
    elif command in ["generate", "gen"]:
        return generate_gallery_only()

    elif command == "serve":
        return serve_gallery()
    
    elif command == "sync":
        sync_args = sys.argv[2:]
        invalid_args = [arg for arg in sync_args if arg not in ["--force", "-f"]]
        if invalid_args:
            print(f"Error: Unknown sync option(s): {' '.join(invalid_args)}")
            print("Usage: sync [--force]")
            return 1

        return sync_git(force=any(arg in ["--force", "-f"] for arg in sync_args))
    
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
