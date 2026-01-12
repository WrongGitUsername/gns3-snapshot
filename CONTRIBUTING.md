# Contributing to GNS3 Thumbnail Generator

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to this project.

## Code of Conduct

This project follows a code of conduct. By participating, you agree to:
- Be respectful and inclusive
- Welcome newcomers
- Focus on what is best for the community
- Show empathy towards others

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected behavior** vs actual behavior
- **Environment details** (OS, Python version, GNS3 version)
- **Code samples** or error messages
- **Screenshots** if applicable

Example bug report:
```markdown
**Environment:**
- OS: Ubuntu 22.04
- Python: 3.10.5
- GNS3 Server: 2.2.42
- Package version: 1.0.0

**Description:**
Thumbnails fail to generate when using node icons.

**Steps to Reproduce:**
1. Run: `gns3-thumbnail --project-ids abc-123 --use-node-icons`
2. See error: "Icon fetch failed"

**Expected:** Thumbnails generated with icons
**Actual:** Error and no output

**Additional Context:**
Error traceback: [paste here]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Include:

- **Clear title** describing the enhancement
- **Detailed description** of the proposed functionality
- **Use cases** and examples
- **Possible implementation** approach (optional)

### Pull Requests

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Make your changes** with clear, atomic commits
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Run tests** and ensure they pass:
   ```bash
   pytest
   black gns3_thumbnail_generator tests
   flake8 gns3_thumbnail_generator tests
   ```
7. **Push to your fork** and submit a pull request

#### Pull Request Guidelines

- Use clear, descriptive titles
- Reference related issues
- Describe changes in detail
- Include before/after examples if applicable
- Keep changes focused and atomic
- Update CHANGELOG.md

Example PR description:
```markdown
## Description
Adds support for custom color schemes for node types.

## Related Issues
Fixes #42

## Changes
- Added `color_scheme` parameter to `GNS3ThumbnailGenerator`
- Updated `_get_node_color()` to use custom schemes
- Added tests for custom color schemes
- Updated documentation

## Testing
- [ ] Added unit tests
- [ ] Manual testing completed
- [ ] Documentation updated

## Screenshots
[Before/after images if applicable]
```

## Development Setup

### Prerequisites

- Python 3.7+
- Git
- Cairo library (for SVG rendering)

### Setup Instructions

1. **Clone your fork:**
   ```bash
   git clone https://github.com/WrongGitUsernamegns3-snapshot/gns3-snapshot.git
   cd gns3-snapshot
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=gns3_thumbnail_generator --cov-report=html

# Run specific test file
pytest tests/test_generator.py

# Run specific test
pytest tests/test_generator.py::test_thumbnail_generation

# Run with verbose output
pytest -v
```

### Code Style

This project uses:
- **Black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking (optional)

```bash
# Format code
black gns3-snapshot tests

# Sort imports
isort gns3-snapshot tests

# Lint
flake8 gns3-snapshot tests

# Type check
mypy gns3-snapshot
```

Pre-commit hooks will automatically run these checks.

## Project Structure

```
gns3-snapshot/
├── __init__.py           # Package initialization
├── generator.py          # Main GNS3ThumbnailGenerator class

tests/
├── __init__.py
├── test_generator.py    # Generator class tests
└── fixtures/            # Test fixtures
```

## Coding Guidelines

### Python Style

- Follow PEP 8
- Use type hints where appropriate
- Write docstrings for public APIs (Google style)
- Keep functions focused and small
- Use meaningful variable names

Example:
```python
def generate_thumbnail(
    self, 
    project_id: str, 
    save_svg: bool = False
) -> Tuple[bool, Optional[str]]:
    """
    Generate a thumbnail for a single project.
    
    Args:
        project_id: GNS3 project UUID
        save_svg: Whether to save intermediate SVG file
        
    Returns:
        Tuple of (success, output_path)
        
    Raises:
        ValueError: If project_id is invalid
    """
    # Implementation
```

### Commit Messages

Follow conventional commits:

- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes (formatting)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Build/tooling changes

Examples:
```
feat: add custom color scheme support
fix: handle missing icon files gracefully
docs: update installation instructions for macOS
test: add tests for parallel processing
```

### Testing Guidelines

- Write tests for new features
- Maintain or improve code coverage
- Use descriptive test names
- Include edge cases
- Mock external dependencies (API calls)

Example test:
```python
def test_thumbnail_generation_success(mock_gns3_api):
    """Test successful thumbnail generation."""
    generator = GNS3ThumbnailGenerator(server_url="http://test:3080")
    success, path = generator.generate_thumbnail("test-project-id")
    
    assert success is True
    assert path is not None
    assert Path(path).exists()
```

## Documentation

### Docstrings

Use Google-style docstrings:

```python
def complex_function(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Brief description of function.
    
    Longer description if needed, explaining what the function does,
    any important behavior, and when to use it.
    
    Args:
        param1: Description of param1
        param2: Description of param2 with default
        
    Returns:
        Dictionary containing results with structure:
        - 'key1': Description
        - 'key2': Description
        
    Raises:
        ValueError: When param1 is empty
        ConnectionError: When server is unreachable
        
    Example:
        >>> result = complex_function("test", param2=20)
        >>> print(result['key1'])
        'value'
    """
```

### README Updates

Update README.md when:
- Adding new features
- Changing public APIs
- Adding configuration options
- Modifying installation steps

## Release Process

(For maintainers)

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release commit:
   ```bash
   git commit -m "chore: release v1.1.0"
   ```
4. Tag the release:
   ```bash
   git tag -a v1.1.0 -m "Release version 1.1.0"
   ```
5. Push changes and tags:
   ```bash
   git push origin main --tags
   ```
6. GitHub Actions will automatically publish to PyPI

## Questions?

- Check existing [issues](https://github.com/yourusername/gns3-thumbnail-generator/issues)
- Start a [discussion](https://github.com/yourusername/gns3-thumbnail-generator/discussions)
- Read the [documentation](https://github.com/yourusername/gns3-thumbnail-generator#readme)

Thank you for contributing! 🎉
