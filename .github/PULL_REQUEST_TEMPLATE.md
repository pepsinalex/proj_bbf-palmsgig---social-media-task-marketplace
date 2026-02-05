## Description

<!-- Provide a brief description of the changes in this PR -->

### What does this PR do?

<!-- Explain the purpose and context of these changes -->

### Related Issue(s)

<!-- Link to related issues (e.g., Fixes #123, Closes #456) -->

---

## Type of Change

<!-- Mark the relevant option with an "x" -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Refactoring (code improvement without changing functionality)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Security patch
- [ ] Dependencies update
- [ ] Configuration change

---

## Testing Performed

<!-- Describe the tests you ran to verify your changes -->

### Test Coverage

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All tests passing locally

### Test Details

<!-- Describe specific test scenarios and results -->

```
# Example:
# - Tested user registration flow with valid/invalid inputs
# - Verified API endpoint returns correct status codes
# - Confirmed database migrations apply successfully
```

---

## Code Quality Checklist

<!-- Ensure all items are checked before requesting review -->

### Code Standards

- [ ] Code follows the project's style guidelines (Black, Ruff)
- [ ] Self-review of code completed
- [ ] Code is properly commented (complex logic explained)
- [ ] No console logs or debug statements left in code
- [ ] Variable and function names are descriptive and clear

### Documentation

- [ ] README updated (if applicable)
- [ ] API documentation updated (if applicable)
- [ ] Inline code comments added for complex logic
- [ ] Docstrings added/updated for public functions

### Dependencies

- [ ] No unnecessary dependencies added
- [ ] All new dependencies are documented
- [ ] Lock files updated (pyproject.toml)
- [ ] Dependencies scanned for vulnerabilities

---

## Security Considerations

<!-- Address security aspects of your changes -->

### Security Checklist

- [ ] No secrets or credentials in code
- [ ] Input validation implemented
- [ ] SQL injection prevention verified
- [ ] XSS protection implemented (if applicable)
- [ ] CSRF protection implemented (if applicable)
- [ ] Authentication/authorization checked
- [ ] Sensitive data properly encrypted
- [ ] Security best practices followed

### Potential Security Impact

<!-- Describe any security implications or considerations -->

---

## Deployment Notes

<!-- Information needed for deploying this change -->

### Database Changes

- [ ] No database changes
- [ ] Database migrations included
- [ ] Migration tested (up and down)
- [ ] Seed data updated (if needed)

### Configuration Changes

- [ ] No configuration changes required
- [ ] Environment variables added/modified (documented below)
- [ ] Secrets need to be updated in production

<!-- List any new environment variables or configuration -->

```
# Example:
# NEW_API_KEY=your_key_here
# MAX_UPLOAD_SIZE=10485760
```

### Deployment Steps

<!-- List any special deployment steps or considerations -->

1. <!-- Step 1 -->
2. <!-- Step 2 -->

### Rollback Plan

<!-- Describe how to rollback if issues occur -->

---

## Screenshots/Videos

<!-- If applicable, add screenshots or videos to demonstrate changes -->

---

## Additional Notes

<!-- Any additional information that reviewers should know -->

### Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

### Performance Impact

<!-- Describe any performance implications (positive or negative) -->

---

## Reviewer Checklist

<!-- For reviewers to complete -->

- [ ] Code changes reviewed and approved
- [ ] Tests are comprehensive and passing
- [ ] Security considerations addressed
- [ ] Documentation is adequate
- [ ] No obvious performance issues
- [ ] Ready to merge

---

**Co-Authored-By:** Claude Sonnet 4.5 <noreply@anthropic.com>
