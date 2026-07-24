# Security Policy

## Supported version

Security fixes are applied to the latest release on the `main` branch.

## Reporting a vulnerability

Please do not publish credentials, connection strings, database passwords, device keys, or security vulnerabilities in a public issue. Contact the maintainer privately through [LinkedIn](https://www.linkedin.com/in/mohamad-ktich) or email `ktichmohamad@gmail.com`.

Include a clear reproduction, affected component, expected impact, and any suggested mitigation. Reports will be acknowledged as soon as practical.

## Deployment requirements

Before any public or industrial deployment:

- Replace every example secret and initial account password.
- Use HTTPS and a managed secret store.
- Disable default seed users.
- Restrict CORS to trusted origins.
- Use least-privilege database credentials.
- Validate uploaded files and configure object-storage access rules.
- Require human approval and industrial safety controls for physical device commands.
- Validate every AI model and threshold on the target factory data.
