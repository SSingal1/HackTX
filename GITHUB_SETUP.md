# Move this project to GitHub

This archive contains the complete frontend sandbox. It includes no backend or live API integrations.

## Existing repository

1. Extract the archive.
2. Copy the contents of toyota-service-guardian into your cloned repository (not the outer folder itself). Merge README files if your repository already has one.
3. Review the files before staging. Do not overwrite existing files without checking differences.
4. From your repository, stage the added files, commit, and push using your normal Git workflow.

## New empty GitHub repository

Create an empty repository on GitHub first. In the extracted toyota-service-guardian folder, run:

```sh
git init
git add .
git commit -m "Add Toyota Smart Service Guardian frontend"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

Replace the username and repository placeholders. If the repository already has commits, clone it and use the existing-repository instructions instead.

## Run and verify

No dependency installation is required. Serve dist with a static HTTP server, such as python -m http.server 8080 --directory dist, then open http://localhost:8080.

With Node installed, run node check.mjs from the project root to verify calculations and page-generation fixtures.

## Main files

- dist/index.html: TFS-inspired homepage
- dist/guardian.html: Smart Service Guardian product page
- dist/styles.css: shared styling
- dist/common.js: shared interface behavior
- dist/home.js: homepage interactions
- dist/guardian.js: product interactions and calculations
- dist/assets/vehicle.svg: local vehicle illustration
- check.mjs: lightweight checks
- README.md: architecture and integration notes

No .git history, deployment identity, API keys or account credentials are included. Keep real provider credentials server-side when implementing the backend.
