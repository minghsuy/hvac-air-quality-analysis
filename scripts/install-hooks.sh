#!/usr/bin/env bash
# Symlink the tracked hooks at scripts/hooks/ into .git/hooks/ so git invokes them.
# Safe to re-run; replaces any existing hook with the symlink.

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

for hook in scripts/hooks/*; do
    name=$(basename "$hook")
    target=".git/hooks/$name"
    ln -sf "../../$hook" "$target"
    chmod +x "$hook"
    echo "installed: $target -> $hook"
done
