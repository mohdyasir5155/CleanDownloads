## Description

Please include a summary of the changes and the related issue (if applicable). Include relevant motivation and context.

Fixes #(issue)

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Classification rule addition or refinement
- [ ] Documentation update
- [ ] Performance or security enhancement
- [ ] Build / CI pipeline update

## Quality & Safety Checklist

- [ ] My code follows the coding style and guidelines of this project.
- [ ] I have verified that all 14 safety invariants documented in `SECURITY.md` are preserved.
- [ ] I have added tests that prove my fix is effective or that my feature works.
- [ ] All new and existing unit tests pass locally (`pytest`).
- [ ] Code passes Ruff static analysis (`ruff check .`).
- [ ] Code passes Bandit security analysis (`bandit -r src/ -ll`).
- [ ] I have updated corresponding documentation (`docs/` and `README.md`) if necessary.
- [ ] No temporary files, credentials, or personal paths are included.
