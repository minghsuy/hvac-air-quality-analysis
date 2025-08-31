#!/bin/bash
# Setup git hooks to prevent committing sensitive information

echo "Setting up git hooks to protect sensitive information..."

# Configure git to use our hooks directory
git config core.hooksPath .githooks

echo "✅ Git hooks configured!"
echo ""
echo "The pre-commit hook will now check for:"
echo "  - Private IP addresses (192.168.x.x)"
echo "  - MAC addresses (d8:3b:da:xx:xx:xx)"
echo "  - Device serials"
echo ""
echo "To test: git commit -m 'test'"