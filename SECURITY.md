# Security Policy

## Supported Versions

Only the latest release on the `main` branch receives security fixes.

| Version | Supported |
|---------|-----------|
| Latest  | ✅        |
| Older   | ❌        |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Send a private report to the maintainers via [GitHub Security Advisories](https://github.com/grey-box/symmetry-project/security/advisories/new).

Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof of concept if possible)
- Any suggested mitigations

We aim to acknowledge reports within **3 business days** and issue a fix within **14 days** for critical issues.

## Known Risk Areas

- **MarianMT / sentence-transformer models** are downloaded from Hugging Face on first use. Pin model versions in `config.default.json` to avoid supply-chain surprises.
- **CORS origins** in `app/main.py` are permissive by default for local development. Restrict them before any network-exposed deployment.
- **`config.json`** (user-local config with potential API keys) is excluded from version control via `.gitignore`. Never commit it.
