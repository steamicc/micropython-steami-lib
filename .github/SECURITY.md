# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest release | Yes |
| older releases | No |

Only the latest release on the `main` branch receives security updates.

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public issue.**

Instead, use one of the following methods:

1. **GitHub Security Advisories** (preferred): use the [Report a vulnerability](https://github.com/steamicc/micropython-steami-lib/security/advisories/new) button on the Security tab of this repository.
2. **Email**: contact the maintainers at [sebastien.nedjar@univ-amu.fr](mailto:sebastien.nedjar@univ-amu.fr).

Please include:

* A description of the vulnerability
* Steps to reproduce or a proof of concept
* The affected version(s)
* Any potential impact

## Response

We will acknowledge your report within **7 days** and aim to provide a fix or mitigation within **30 days**, depending on severity.

## Scope

This policy covers the MicroPython driver library code in `lib/` and the build/CI tooling. It does **not** cover:

* The MicroPython firmware itself (report upstream at [micropython/micropython](https://github.com/micropython/micropython))
* The STeaMi board hardware
* Third-party npm dependencies (report upstream to the respective package maintainers)

## Automated Security

This repository uses:

* **Dependabot** for automated dependency vulnerability alerts
* **CodeQL** for static analysis on CI workflows
* **Secret scanning** for detecting leaked credentials
