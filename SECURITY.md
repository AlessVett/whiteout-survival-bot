# Security Policy

## Supported Versions

Currently, we support security updates for the following versions:

| Version | Supported |
|---------|-----------|
| 1.0.1   | ✅         |
| < 1.0.1 | ❌         |

## Reporting a Vulnerability

We take the security of DWOS seriously. If you believe you have found a security vulnerability, please report it to us as described below.

### Please do NOT:
- Open a public issue on GitHub
- Post about the vulnerability on social media
- Exploit the vulnerability for malicious purposes

### Please DO:
- Email us at: support@wos-2630.fun
- Provide detailed steps to reproduce the vulnerability
- Include the impact and potential risks
- Suggest a fix if you have one

### What to expect:
1. **Acknowledgment**: We'll acknowledge receipt of your report within 48 hours
2. **Investigation**: We'll investigate and validate the issue within 7 days
3. **Resolution**: We'll work on a fix and coordinate disclosure timing with you
4. **Credit**: We'll credit you for the discovery (unless you prefer to remain anonymous)

## Security Best Practices

When using DWOS, please ensure:

### For Bot Operators:
- Keep your `.env` file secure and never commit it to version control
- Use strong, unique bot tokens and rotate them regularly
- Limit bot permissions to only what's necessary
- Regularly update dependencies to patch known vulnerabilities
- Monitor bot activity for suspicious behavior

### For Developers:
- Never hardcode sensitive information (tokens, passwords, API keys)
- Validate and sanitize all user inputs
- Use parameterized queries for database operations
- Implement rate limiting on API endpoints
- Keep dependencies up to date
- Follow the principle of least privilege

### Environment Variables Security:
Required sensitive environment variables:
- `DISCORD_TOKEN`: Discord bot token
- `MONGODB_URI`: MongoDB connection string
- `GUILD_ID`: Authorized server ID

## Security Features

DWOS implements several security measures:

1. **Guild Restrictions**: Bot only operates in authorized servers defined by `GUILD_ID`
2. **Role-based Access**: Commands are restricted based on Discord roles and permissions
3. **Data Privacy**: GDPR-compliant data handling with user consent and data deletion options
4. **Input Validation**: All user inputs are validated and sanitized
5. **Rate Limiting**: API calls and commands are rate-limited to prevent abuse
6. **Secure Storage**: Sensitive data is encrypted at rest in MongoDB

## Vulnerability Disclosure Policy

We follow a coordinated disclosure process:

1. Security issues are kept confidential until a fix is available
2. We aim to release patches within 30 days of validation
3. Critical vulnerabilities may trigger immediate hotfixes
4. We'll publish security advisories for significant issues

## Dependencies

We regularly audit our dependencies for known vulnerabilities using:
- GitHub Dependabot
- `pip-audit` for Python packages
- Manual review of critical dependencies

## Contact

For security-related inquiries:
- Email: support@wos-2630.fun
- GitHub Security Advisories: [Create private advisory](https://github.com/AlessVett/whiteout-survival-bot/security/advisories/new)

## Recognition

We appreciate the security research community and will acknowledge reporters who:
- Follow responsible disclosure practices
- Provide clear, reproducible reports
- Work with us to understand and resolve issues

Thank you for helping keep DWOS secure! 🛡️