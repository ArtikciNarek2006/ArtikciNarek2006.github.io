# Project Gallery System

A modular, automated project gallery system with CLI tools and GitHub Actions deployment pipeline.

## 🎯 Quick Start

### Activation

**Linux/macOS:**
```bash
source .internal/bin/activate.sh
```

**Windows PowerShell:**
```powershell
. .internal\bin\activate.ps1
```

**Windows CMD:**
```cmd
.internal\bin\activate.cmd
```

### Available Commands

Once activated, use the `gallery` command:

```bash
# Create a new project
gallery create my-awesome-project

# Update project metadata
gallery update my-awesome-project  # Update single project
gallery update all                  # Update all projects

# Remove a project
gallery remove old-project

# Generate and serve gallery locally
gallery serve

# Sync changes to git
gallery sync
gallery sync --force         # Backup remote branch, then overwrite origin with local state

# Migrate project to new repo
gallery migrate my-project https://github.com/user/new-repo.git

# Deactivate environment
deactivate_gallery

# Get help
gallery help
```

## 📁 Directory Structure

```
.
├── .github/
│   └── workflows/
│       └── deploy.yml           # GitHub Actions deployment
├── .internal/
│   ├── bin/
│   │   ├── activate.sh          # Unix/Linux/macOS activation
│   │   ├── activate.ps1         # PowerShell activation
│   │   ├── activate.cmd         # Windows CMD activation
│   │   └── cli.py               # Main CLI script
│   ├── generative_galery/
│   │   └── generator.py         # Gallery generation logic
│   ├── requirements.txt         # Python dependencies
│   └── venv/                    # Virtual environment (auto-created)
├── projects/
│   └── [project_name]/
│       ├── .project_info/
│       │   ├── info.json        # Project metadata
│       │   └── images/          # Project screenshots
│       ├── index.html           # Project entry point
│       ├── style.css            # Project styles
│       └── script.js            # Project scripts
└── index.html                   # Generated gallery (auto-generated)
```

## 🎨 Project Info Structure

Each project must have a `.project_info/info.json` file:

```json
{
    "id": "unique-uuid",
    "title": "Project Title",
    "desciption_short": "Brief description",
    "description_long": "Detailed description",
    "icon_file_name": "icon.png",
    "images": ["screenshot1.png", "screenshot2.png"],
    "github_url": "https://github.com/user/repo",
    "tags": ["Tag1", "Tag2"],
    "date_published": "2024-05-20",
    "version": "1.0.0"
}
```

## ✨ Gallery Features

- **🕐 Animated Clock Preview** - Full-page clock with smooth animations
- **📊 GitHub Statistics** - Live repo stats fetched from GitHub API
- **💾 Storage Manager** - Modal popup to view, **edit**, and flush localStorage/sessionStorage
- **👁️ View Modes** - Grid, List (with images), Compact List (no images)
- **🎨 Themes** - Light, Dark, and OLED Black modes
- **🎞️ Auto-Play Slideshow** - Hover over icon to auto-cycle through images (1.5s interval)
- **🖼️ Smart Icon Layout** - 120x120px thumbnail next to description
- **🔍 Live Search** - Real-time filtering by title/description
- **🏷️ Tag Filtering** - Filter projects by tags
- **📅 Sorting** - Sort by date or name (ascending/descending)

## 🚀 Deployment

The gallery automatically deploys to GitHub Pages via GitHub Actions when you push to the main branch.

### Setup GitHub Pages:

1. Go to repository Settings → Pages
2. Source: GitHub Actions
3. Push changes to trigger deployment

## 🛠️ Development Workflow

1. **Create a new project:**
   ```bash
   gallery create my-project
   ```

2. **Add images to** `.project_info/images/`

3. **Edit** `info.json` **with project details**

4. **Test locally:**
   ```bash
   gallery serve
   ```

5. **Sync to GitHub:**
   ```bash
   gallery sync
   ```

6. **Deploy automatically via GitHub Actions**

## 📋 Requirements

- Python 3.8+
- Git
- Modern web browser

## 🔧 Troubleshooting

**Virtual environment issues:**
- Delete `.internal/venv/` and re-run activation script

**Gallery not generating:**
- Run `gallery update all` to validate project data
- Check console for error messages

**Images not showing:**
- Ensure images are in `.project_info/images/`
- Verify filenames in `info.json` match actual files

## 📝 License

This project gallery system is open source and available for use.
