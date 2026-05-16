# Security Policy

## Supported Versions

Security updates are currently provided for the following branches:

| Version / Branch | Supported |
| --- | --- |
| `main` | Yes |
| Active release branches | Yes |
| Deprecated branches | No |
| Archived repositories | No |

Security fixes are applied to `main` first. Backports to release branches are handled based on severity, exploitability, and maintenance status.

## Reporting a Vulnerability

Please do not open a public GitHub issue for security vulnerabilities.

To report a vulnerability, use GitHub's private vulnerability reporting feature by clicking **Report a vulnerability** on the repository Security page.

When reporting a vulnerability, please include:

- Affected repository
- Affected branch or version
- Vulnerability description
- Steps to reproduce
- Proof of concept, if available
- Potential impact
- Suggested fix, if known

We ask that reporters follow responsible disclosure and give RedTeam maintainers reasonable time to investigate and remediate before public disclosure.

## Response Timeline

| Severity | Acknowledgement | Initial Assessment | Target Resolution |
| --- | --- | --- | --- |
| Critical | 1 business day | 3 business days | As soon as possible |
| High | 2 business days | 5 business days | 14 business days |
| Medium | 5 business days | 10 business days | 30 days |
| Low | 10 business days | 15 business days | Best effort |

Timelines may vary depending on complexity, dependency ownership, upstream fixes, and release coordination.

## Scope

The following are in scope:

- Vulnerabilities in RedTeam-owned source code
- Vulnerable dependencies used by RedTeam repositories
- GitHub Actions workflow vulnerabilities
- Dockerfile or container security issues
- Authentication or authorization issues
- Access control problems
- Sensitive data exposure
- Secret leakage in repository history or workflows

## Out of Scope

The following are out of scope:

- Social engineering
- Physical attacks
- Denial-of-service testing
- Spam or phishing reports unrelated to RedTeam code
- Issues requiring compromised accounts
- Reports from automated scanners without clear impact
- Missing security headers on non-production systems
- Vulnerabilities in third-party services not controlled by RedTeam

## Disclosure Process

After receiving a report, RedTeam maintainers will:

1. Acknowledge the report.
2. Validate and reproduce the issue.
3. Determine severity and affected versions.
4. Develop and test a fix.
5. Release a patch or mitigation.
6. Credit the reporter if requested and appropriate.

## Security Updates

Security fixes may be released through:

- Direct commits to the default branch
- Patch releases
- Dependency update pull requests
- GitHub Security Advisories
- Release notes or changelog entries

Thank you for helping keep RedTeam secure.
