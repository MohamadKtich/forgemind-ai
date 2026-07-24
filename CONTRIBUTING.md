# Contributing to ForgeMind AI

Thank you for helping improve ForgeMind AI.

## Development workflow

1. Fork the repository and create a focused branch.
2. Copy the environment examples; never commit real secrets.
3. Keep backend changes covered by tests.
4. Run the verification commands before opening a pull request.
5. Update documentation when behavior, configuration, or model assumptions change.

```bash
cd backend
pytest -q
python -m compileall app ml

cd ../frontend
npm ci
npm run typecheck
npm run build
```

## Pull requests

Describe the problem, the implementation, screenshots for UI changes, test evidence, and any migration or model-impact notes. Keep pull requests small enough to review sensibly, a standard humans invented after discovering that 4,000-line surprise diffs are unpleasant.

## AI and dataset claims

Do not describe a model as trained on a dataset unless the repository includes reproducible evidence: dataset provenance, split method, saved weights, evaluation metrics, and limitations. Keep licenses and commercial-use restrictions explicit.
