# Contributing to InstaFlow

Thank you for your interest in contributing to InstaFlow! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and considerate in all interactions.

## How Can I Contribute?

### Reporting Bugs

Before creating a bug report:

1. Check the existing issues to see if the problem has already been reported
2. If you're unable to find an open issue addressing the problem, create a new one
3. Use the provided template and fill in as much detail as possible
4. Include steps to reproduce, expected and actual behavior, screenshots, and any other relevant information

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion:

1. Use a clear and descriptive title
2. Provide detailed explanation of the suggestion
3. Explain why this enhancement would be useful
4. List possible implementation steps if you have ideas

### Pull Requests

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes following our commit message conventions
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request against the `develop` branch

## Development Environment Setup

1. Clone your fork of the repository
2. Create and activate a virtual environment
3. Install development dependencies:
   ```
   pip install -r requirements-dev.txt
   ```
4. Install the package in development mode:
   ```
   pip install -e .
   ```

## Style Guidelines

### Code Style

We follow PEP 8 style guidelines with the following additions:

- Maximum line length: 100 characters
- Use 4 spaces for indentation (no tabs)
- Use double quotes for docstrings and single quotes for regular strings

### Commit Messages

- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- First line is a concise summary (max 50 characters)
- Body should explain what and why vs. how
- Reference issues and pull requests when relevant

Example:
```
Add user follower retrieval feature

- Implement get_user_followers method in InstagramBot
- Add pagination support for follower lists
- Add rate limit checks to prevent detection

Closes #123
```

## Testing

All new features should include appropriate tests. Run the test suite with:

```
pytest
```

To check code coverage:

```
pytest --cov=src tests/
```

We aim for a minimum test coverage of 80%.

## Documentation

- All modules, classes, and methods should have proper docstrings
- Follow Google style for docstrings
- Include type hints for all function parameters and return values
- Update README.md and other documentation when adding or changing features

## Versioning

We use [Semantic Versioning](https://semver.org/) for releases:

- MAJOR version for incompatible API changes
- MINOR version for backwards-compatible functionality
- PATCH version for backwards-compatible bug fixes

## Branching Strategy

- `main`: Production-ready code
- `develop`: Integration branch for features
- `feature/*`: Feature branches
- `bugfix/*`: Bug fix branches
- `release/*`: Release preparation branches
- `hotfix/*`: Hotfix branches for critical issues

## Review Process

All pull requests will go through a review process:

1. Automated tests must pass
2. Code quality checks must pass
3. At least one maintainer must approve
4. No merge conflicts or requested changes pending

## Thank You!

Your contributions to InstaFlow are greatly appreciated. Thank you for helping make this project better!