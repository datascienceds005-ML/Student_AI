# Deployment Guide: GitHub → Hugging Face Spaces

## Part 1: Push to GitHub

```bash
cd universal-ecommerce-dashboard
git init
git add .
git commit -m "Initial commit: Universal E-Commerce Analytics Dashboard"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git
git push -u origin main
```

(If you created the repo on GitHub's website first with a README already
in it, run `git pull origin main --allow-unrelated-histories` before
pushing, or just delete the GitHub-created README and push cleanly.)

## Part 2: Create a Hugging Face Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Space name**: e.g. `universal-ecommerce-dashboard`
   - **License**: your choice (e.g. MIT)
   - **Select the Space SDK**: choose **Streamlit**
   - **Space hardware**: CPU basic (free tier) is enough for this app
3. Click **Create Space**.

## Part 3: Connect your GitHub repo to the Space

You have two options:

### Option A — Push directly to the Space's own git remote (simplest)
Hugging Face gives every Space its own git repo. After creating the
Space, HF shows you a remote URL like:
```
https://huggingface.co/spaces/<your-username>/universal-ecommerce-dashboard
```
Add it as a second remote and push your existing code to it:
```bash
git remote add hf https://huggingface.co/spaces/<your-username>/universal-ecommerce-dashboard
git push hf main
```
You'll be prompted for your Hugging Face username and an **access token**
(create one at https://huggingface.co/settings/tokens with "write" scope
— use the token as the password, not your account password).

### Option B — GitHub Actions auto-sync (keeps GitHub as the source of truth)
Add a `.github/workflows/sync-to-hf.yml` file (see below) so every push
to GitHub `main` automatically syncs to your HF Space. This is the
recommended setup for the workflow you described (edit/upload on GitHub,
auto-deploy to HF).

```yaml
name: Sync to Hugging Face Spaces
on:
  push:
    branches: [main]
jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Push to Hugging Face
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          git remote add hf https://user:$HF_TOKEN@huggingface.co/spaces/<your-username>/universal-ecommerce-dashboard
          git push hf main --force
```
You'd add `HF_TOKEN` as a GitHub repo secret (Settings → Secrets and
variables → Actions → New repository secret) using a Hugging Face write
token as the value.

## Part 4: Verify the deployment

- HF Spaces automatically reads `requirements.txt` and installs
  dependencies, then runs the `app_file` specified in the README's YAML
  header (already set to `app.py` in the README provided).
- Build logs are visible on your Space's page under the "Logs" tab — check
  here first if the app fails to start.
- Once built, your app is live at:
  `https://huggingface.co/spaces/<your-username>/universal-ecommerce-dashboard`

## Common issues

| Problem | Likely cause | Fix |
|---|---|---|
| Space stuck "Building" | Missing dependency | Check Logs tab; add missing package to `requirements.txt` |
| "File not found: app.py" | `app_file` in README YAML doesn't match your filename | Ensure README.md top YAML has `app_file: app.py` |
| App builds but shows blank page | Exception on first run (e.g. missing sample data path) | Check Logs tab; the app is designed to only need an uploaded file, no local paths required |
| Upload fails for large files | HF free tier has request size limits | Should be fine under ~200MB but very large files may need Spaces persistent storage or a paid tier |
