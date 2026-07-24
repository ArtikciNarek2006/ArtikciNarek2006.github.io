# Project Gallery System

A small gallery system for organizing projects, generating a root `index.html`, and optionally publishing it through GitHub Pages.

## What this repo is for

- Keep each project isolated in `projects/<project_name>/`
- Store project metadata in `.project_info/info.json`
- Generate one root `index.html` that lists all projects
- Preview locally with `gallery serve`
- Use GitHub Pages if you want automatic deployment

## Requirements

- Python 3.8+
- Git
- A modern web browser

## Activate the environment

Linux/macOS:

```bash
source .internal/bin/activate.sh
```

Windows PowerShell:

```powershell
. .internal\bin\activate.ps1
```

Windows CMD:

```cmd
.internal\bin\activate.cmd
```

## Main workflow

1. Create or update projects inside `projects/`.
2. Edit each project's `.project_info/info.json`.
3. Run `gallery update all` to validate the project data.
4. Run `gallery generate` or `gallery gen` to build the root `index.html`.
5. Open locally with `gallery serve` if you want a preview.
6. Commit the generated `index.html` after changes.

## Commands

Create a project:

```bash
gallery create my-project
```

Update metadata:

```bash
gallery update my-project
gallery update all
```

Generate the gallery only:

```bash
gallery generate
gallery gen
```

Serve locally:

```bash
gallery serve
```

Notes:

- `gallery generate` and `gallery gen` only build `index.html`.
- `gallery serve` generates the gallery first, then starts a local server.
- If port `8000` is busy, `gallery serve` automatically uses the next free port.

Other commands:

```bash
gallery remove old-project
gallery sync
gallery sync --force
gallery migrate my-project https://github.com/user/new-repo.git
gallery help
```

## `gallery migrate`

Use `gallery migrate` when you want to move one existing project into a new standalone Git repository.

What it does:

- Copies the selected project from `projects/<name>/` into a temporary working folder.
- Removes the `.project_info/` directory because that data is specific to this gallery repo.
- Updates project HTML files so the old "Back to Gallery" link is removed.
- Initializes a new Git repository in the temporary copy.
- Creates an initial commit and adds the new remote URL.
- Offers to push the new repo immediately, or lets you keep the prepared copy for manual pushing later.

What it does not do:

- It does not modify the original project inside this gallery repository.
- It does not migrate the full gallery or any sibling projects.
- It does not keep gallery-specific metadata such as `.project_info/` in the target repo.

When to use it:

- Use it when a project should leave the gallery and become its own repo.
- Use it when you want to reuse the project files but not the gallery structure.
- Use it when the new repository should start clean with only the project content.

Example:

```bash
gallery migrate my-project https://github.com/user/new-repo.git
```

Typical flow:

1. Make sure the project exists in `projects/my-project/`.
2. Run `gallery migrate my-project <new-repo-url>`.
3. Review the temporary copy that the command prepares.
4. Choose whether to push immediately or push later yourself.

Notes:

- The command asks for GitHub credentials when it needs to push to a remote.
- If you answer `no`, the command leaves the prepared repo in the temporary folder for manual use.
- The original gallery project remains in place until you remove it separately.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── deploy.yml
├── .internal/
│   ├── bin/
│   │   ├── activate.sh
│   │   ├── activate.ps1
│   │   ├── activate.cmd
│   │   └── cli.py
│   ├── generative_galery/
│   │   └── generator.py
│   ├── requirements.txt
│   └── venv/
├── projects/
│   └── [project_name]/
│       ├── .project_info/
│       │   ├── info.json
│       │   └── images/
│       ├── index.html
│       ├── style.css
│       └── script.js
└── index.html
```

## Project metadata

Each project needs a `.project_info/info.json` file.

Example:

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

Required fields should be kept valid, but the generator will fall back to defaults when some data is missing.

## Why this structure is useful

- Each project keeps its own assets and metadata in one place.
- The generated root `index.html` gives you a single entry point for the whole gallery.
- The gallery can be previewed locally without extra setup.
- The same generated output can be committed for GitHub Pages or used as a static site later.

## Using with GitHub

If you want GitHub to publish the gallery, commit the generated root `index.html` after you update projects and run `gallery generate` or `gallery gen`.

Typical flow:

```bash
gallery update all
gallery generate
git add index.html projects/
git commit -m "Update gallery"
git push
```

The repository already includes a GitHub Actions workflow in `.github/workflows/deploy.yml`.

If you do not want to use GitHub Actions for a project, move `.github` to `.github_disabled` and commit that change manually. You can move it back later when you want the workflow again.

## GitHub credentials

The CLI automatically reads GitHub credentials from a root `.env` file when it needs to talk to `github.com` over HTTPS.

Use these variables:

- `GITHUB_USERNAME`
- `GITHUB_PASSWORD`

The file is loaded automatically for commands like `gallery sync`, `gallery sync --force`, and `gallery migrate` when they need to push to GitHub.

Use the provided `template.env` file as a starting point, then copy it to `.env` and fill in your values.

## GitHub Pages setup

1. Open repository Settings.
2. Go to Pages.
3. Set Source to GitHub Actions.
4. Push changes that include the generated `index.html`.

## Gallery features

- Search by title or description
- Filter by tags
- Sort by name or date
- Switch between grid and list-style views
- Use themes for different display preferences
- Preview project images with automatic cycling

## Troubleshooting

If the gallery does not update correctly:

- Run `gallery update all` first.
- Check `.project_info/info.json` for invalid JSON or missing fields.
- Make sure image files exist in `.project_info/images/`.
- Regenerate the gallery with `gallery generate`.

If local preview fails:

- Use `gallery serve` again; it will pick another port if `8000` is already used.
- Check for terminal errors from Python or Git.

If you changed project data and use GitHub Pages:

- Regenerate `index.html`.
- Commit the new root `index.html`.
- Push the commit to the repository.

## License

This project gallery system is open source and available for use.
