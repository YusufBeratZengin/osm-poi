# Security Policy

## Supported Versions

Security updates are provided for the latest minor release line.

| Version | Supported | Notes |
|---|---|---|
| 0.1.x | Yes | Active release branch |
| < 0.1.0 | No | Pre-release versions |

## Reporting a Vulnerability

Please do not open a public issue for potential security vulnerabilities.

Use GitHub's private vulnerability reporting feature on the repository:
<https://github.com/YusufBeratZengin/osm-poi/security/advisories/new>

When filing a report, please include:
- A clear description of the vulnerability and its potential impact.
- Step-by-step instructions or proof-of-concept code to reproduce the issue.
- The version of `osm-poi`, Python version, and operating system used.

### Response Timeline

- **Initial Acknowledgement**: Within 48 hours.
- **Assessment and Fix Plan**: Within 7 business days.
- **Security Release**: Prompt release of a patched version accompanied by a security advisory, crediting the reporter if desired.

## Security Architecture & Design Principles

`osm-poi` incorporates multiple defense-in-depth measures:

1. **Protocol Restriction**: Only `http://` and `https://` URLs are accepted. `file://`, `ftp://`, and local schemes are blocked to avoid SSRF or unauthorized file access.
2. **Query Sanitization**: Preset keys and values inserted into Overpass QL queries are strictly validated and escaped against query injection.
3. **CSV Formula Injection Mitigation**: Any exported cell starting with dangerous characters (`=`, `+`, `-`, `@`, `\t`, `\r`) is neutralized with a leading single quote (`'`) to protect spreadsheet users.
4. **No Credential Storage**: `osm-poi` does not store, request, or persist passwords, tokens, or private secrets. Only a User-Agent identifying contact information is transmitted.
5. **Area Limiting**: Enforces a default area limit (`0.25` sq degrees) to prevent denial-of-service on public OpenStreetMap community servers.
