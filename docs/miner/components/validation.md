---
title: About Validation
---

## Validation Overview

The Validation Service is a critical component of the RedTeam Subnet that ensures all miner submissions meet security, integrity, and fairness standards. It performs comprehensive checks on your code before it can be accepted for scoring and rewards.

## What Gets Validated?

When you submit code to a challenge, it goes through multiple validation checks:

### Code Linting

Your code is automatically scanned for code quality, style issues, and potential problems:

- **JavaScript Challenges**: Uses ESLint to check for:
    - Code style violations
    - Potential bugs and suspicious patterns
    - Performance issues
    - Security vulnerabilities
  
- **Python Challenges**: Uses Pylint to check for:
    - Code quality and maintainability
    - Style consistency
    - Potential bugs and issues
    - Type checking problems

### Submission Integrity

Beyond linting, validation checks that your submission:

- **Has required files**: All files needed for the challenge are present
- **Includes necessary functions**: All required functions or exports exist
- **Contains no extraneous code**: No unnecessary functions, methods, or classes that could:
    - Affect benchmark performance
    - Bypass or interfere with validation checks
    - Skew comparison results against other miners
    - Manipulate scoring in unfair ways

- **Follows challenge specifications**: Your code adheres to the specific challenge requirements
- **Is properly structured**: Code organization meets expectations

### Comparison Readiness

Validation also ensures your submission is ready for fair comparison:

- **Code is legitimate**: No obfuscation or intentionally confusing patterns
- **No plagiarism indicators**: Code structure is reasonable and not obviously copied
- **Performance optimization only**: No artificial performance tricks or exploits

!!! warning "Validation is Strict"
    The validation system is designed to be thorough and fair. If your submission contains any extraneous code, unused functions, or attempts to bypass checks, it will be marked as **Invalid**. This ensures all miners compete on equal footing.

## Why Validation Matters

### For You (The Miner)

- **Transparency**: You know exactly what requirements your code must meet
- **Fairness**: All miners are held to the same validation standards
- **Quality Assurance**: Your code is confirmed to work and meet requirements before scoring
- **Early Feedback**: Invalid submissions are caught immediately, letting you fix issues quickly

### For the Network

- **Security**: Prevents malicious code from affecting network operations
- **Fairness**: Eliminates unfair advantages from code tricks or exploits
- **Accuracy**: Ensures comparisons between submissions are meaningful and fair
- **Consistency**: All submissions meet the same quality standards

## Testing Your Code

### Before Submission

!!! tip "Use the Testing Playground"
    RedTeam provides a [Testing Playground](https://replit.com/@redteamsn61/absnifferv1eslintcheck?v=2#README.md) where you can:
    - Test your code against linting rules
    - Verify it passes validation checks
    - Check for any issues before submitting
    - See exactly what validators will test

The playground uses the exact same linting and validation rules as the production system, so you can be confident your code will pass.

### Local Testing

Before using the playground, you can test locally:

```bash
# For JavaScript challenges
npm install
npm run lint  # Run ESLint

# For Python challenges
pip install -r requirements.txt
pylint src/  # Run Pylint
```

## When Validation Fails

If your submission fails validation, you'll see an **"Invalid"** status on your dashboard.

### What to Do

1. **Check the Note column**: Look for error messages explaining what failed
2. **Review Validation Output**: Click the "Validation Output" payload to see details
3. **Fix the issues**: Common problems include:
    - Linting errors (style, syntax, code quality)
    - Missing required functions or files
    - Extraneous code that shouldn't be there
    - Code that doesn't follow challenge specifications

4. **Test again**: Use the Testing Playground to verify your fixes
5. **Resubmit**: Once fixed, submit a new version

### Example Issues

**Too much code**:
```javascript
// ❌ Don't do this - has extra functions
function myChallenge() { /* ... */ }
function helperFunction() { /* ... */ }
function anotherHelper() { /* ... */ }
function unused() { /* ... */ }  // This will fail validation

// ✅ Do this - only required code
function myChallenge() { /* ... */ }
```

**Code style issues**:
```python
# ❌ Don't do this
def myFunc( ):  # Extra spaces
    x=1+2  # Style issues
    return x

# ✅ Do this
def my_func():
    x = 1 + 2
    return x
```

## Validation vs. Scoring vs. Acceptance

These are three different processes:

| Process | What It Does | Outcome |
|---------|------------|---------|
| **Validation** | Checks code quality, structure, and compliance | Valid or Invalid |
| **Scoring** | Evaluates how well your code solves the challenge | Numeric score (0.0 - 1.0) |
| **Acceptance** | Determines if you earn rewards based on validation + score + penalty | Accepted or Rejected |

**Flow**: Validation → Scoring → Acceptance Check

A submission must be **Valid** before it can even be scored. If it's Invalid, the process stops there.

## Best Practices

### Before Submitting

1. ✅ **Run the linter locally** to catch style issues early
2. ✅ **Test in the playground** to verify validation will pass
3. ✅ **Remove all unnecessary code** - keep only what's required
4. ✅ **Follow the challenge specs exactly** - don't add extras
5. ✅ **Check for common issues** - unused functions, wrong file structure, missing files

### During Development

1. ✅ **Keep code clean and simple** - easier to understand and less likely to fail validation
2. ✅ **Follow naming conventions** - use standard names for functions and variables
3. ✅ **Comment your code** - helps validators understand your approach
4. ✅ **Test frequently** - catch issues early before final submission
5. ✅ **Read error messages carefully** - they tell you exactly what's wrong

### When You Get Invalid

1. ✅ **Don't ignore it** - Invalid status means real problems exist
2. ✅ **Review the output carefully** - the error messages are specific
3. ✅ **Fix one issue at a time** - makes it easier to identify what was wrong
4. ✅ **Test again before resubmitting** - verify your fixes work
5. ✅ **Compare to the playground** - see if playground and your code match

!!! info "Validation Helps You Win"
    The validation system isn't meant to punish miners - it's designed to ensure fair competition. When everyone's code is validated equally, your actual solution quality determines your success, not tricks or exploits.

## Related Topics

- See each [Challenges](../../challenges/README.md) requirements for specific validation rules 
- See [Dashboard Documentation](dashboard.md) to understand how to interpret your validation results
- See [Status Lifecycle](dashboard.md#submission-status-lifecycle) for details on the Invalid status
- Visit the [Testing Playground](https://replit.com/@redteamsn61/absnifferv1eslintcheck?v=2#README.md) to test your code before submitting
