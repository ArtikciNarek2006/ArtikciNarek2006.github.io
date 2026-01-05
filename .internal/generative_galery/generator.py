"""
Gallery Generator - Scans projects and generates index.html

This module scans the projects/ directory and generates a fancy gallery
index.html with robust error handling for missing or corrupt data.
"""

import json
from pathlib import Path
from datetime import datetime

# Constants
REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
PROJECTS_DIR = REPO_ROOT / "projects"
OUTPUT_FILE = REPO_ROOT / "index.html"
TEMPLATES_DIR = Path(__file__).parent / "templates"

def load_project_info(project_dir):
    """
    Load project info.json with fallback handling.
    
    Returns a dict with all necessary fields, using placeholders if data is missing.
    """
    info_path = project_dir / ".project_info" / "info.json"
    project_name = project_dir.name
    
    # Default fallback data
    fallback = {
        "id": f"fallback-{project_name}",
        "title": project_name.replace("_", " ").title(),
        "desciption_short": f"A {project_name} project",
        "description_long": f"No detailed description available for {project_name}.",
        "icon_file_name": "icon.png",
        "images": [],
        "github_url": "None",
        "tags": ["Uncategorized"],
        "date_published": "2024-01-01",
        "version": "1.0.0",
        "project_path": project_name
    }
    
    # Try to load actual info
    if not info_path.exists():
        print(f"  Warning: {project_name}/info.json not found, using fallback")
        fallback["project_path"] = project_name
        return fallback
    
    try:
        with open(info_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        # Merge with fallback to ensure all fields exist
        for key, value in fallback.items():
            if key not in info:
                info[key] = value
        
        info["project_path"] = project_name
        
        # Validate images exist
        images_dir = project_dir / ".project_info" / "images"
        if images_dir.exists():
            valid_images = []
            for img in info.get("images", []):
                img_path = images_dir / img
                if img_path.exists():
                    valid_images.append(f"projects/{project_name}/.project_info/images/{img}")
                else:
                    print(f"  Warning: {project_name} - image {img} not found")
            info["images_full_paths"] = valid_images
        else:
            info["images_full_paths"] = []
        
        # Set icon path
        icon_file = info.get("icon_file_name", "icon.png")
        icon_path = images_dir / icon_file if images_dir.exists() else None
        if icon_path and icon_path.exists():
            info["icon_path"] = f"projects/{project_name}/.project_info/images/{icon_file}"
        else:
            info["icon_path"] = None
        
        return info
        
    except json.JSONDecodeError as e:
        print(f"  Error: {project_name}/info.json is corrupted: {e}")
        print(f"  Using fallback data for {project_name}")
        return fallback
    except Exception as e:
        print(f"  Error loading {project_name}: {e}")
        return fallback

def scan_projects():
    """Scan projects directory and return list of project info."""
    if not PROJECTS_DIR.exists():
        print("Warning: Projects directory not found")
        return []
    
    projects = []
    
    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue
        
        # Skip hidden directories
        if project_dir.name.startswith("."):
            continue
        
        info = load_project_info(project_dir)
        projects.append(info)
    
    return projects

def load_template(filename):
    """Load a template file from the templates directory."""
    template_path = TEMPLATES_DIR / filename
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

def generate_html(projects):
    """Generate the gallery HTML content."""
    
    # Load templates
    html_template = load_template("index.html")
    css_content = load_template("styles.css")
    js_content = load_template("main.js")
    
    # Build projects JSON for JavaScript
    projects_json = json.dumps(projects, indent=2, ensure_ascii=False)
    
    # Replace placeholders in HTML template
    html = html_template.replace("{{CSS_CONTENT}}", css_content)
    html = html.replace("{{PROJECTS_DATA}}", projects_json)
    html = html.replace("{{JAVASCRIPT_CONTENT}}", js_content)
    
    return html


def generate_gallery():
    """Main function to generate the gallery."""
    print("Scanning projects...")
    projects = scan_projects()
    
    print(f"Found {len(projects)} project(s)")
    
    print("Generating HTML...")
    html = generate_html(projects)
    
    print(f"Writing to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    
    print(f"✓ Gallery generated successfully at {OUTPUT_FILE}")
    return True

if __name__ == "__main__":
    generate_gallery()
