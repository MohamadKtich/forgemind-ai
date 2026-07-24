# Publishing ForgeMind AI on GitHub

## Recommended repository

- Repository name: `forgemind-ai`
- Description: `Agentic industrial AI platform for predictive maintenance, visual quality control, production intelligence, digital twin workflows, and factory operations.`
- Visibility: Public
- License: MIT

## Recommended topics

```text
agentic-ai
industrial-ai
predictive-maintenance
smart-manufacturing
computer-vision
quality-control
digital-twin
factory-automation
fastapi
nextjs
machine-learning
opencv
supabase
postgresql
bilingual
```

## Push commands

Open CMD or PowerShell inside the project folder:

```bash
git init
git branch -M main
git config user.name "Mohamad Abdullatif Ktich"
git config user.email "YOUR_GITHUB_EMAIL"
git add .
git commit -m "Initial release of ForgeMind AI"
git remote add origin https://github.com/MohamadKtich/forgemind-ai.git
git push -u origin main
```

## Before pushing

```bash
python scripts/preflight_release.py
```

Confirm that the repository does not contain:

- `backend/.env`
- `frontend/.env.local`
- Supabase connection strings
- API keys or private keys
- local databases
- uploaded factory images or reports
- proprietary factory data

## GitHub settings

After the first push:

1. Add the description and topics above.
2. Upload `assets/github-social-preview.png` under **Settings → General → Social preview**.
3. Enable Issues and Discussions if desired.
4. Protect `main` and require the CI workflow before merges.
5. Create a release from the latest commit and attach the source ZIP only if needed.
