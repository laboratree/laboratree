#!/usr/bin/env bash
# Enable this repo's git hooks (.githooks/) for your clone. Run once after cloning.
#   Git hooks in .git/hooks aren't shared; pointing core.hooksPath at the tracked
#   .githooks/ folder gives everyone the same pre-commit / pre-push gates.
set -euo pipefail
root="$(git rev-parse --show-toplevel)"
git -C "$root" config core.hooksPath .githooks
echo "✓ git hooks enabled (core.hooksPath = .githooks)"
echo "  pre-commit: ruff + tsc on staged files   |   pre-push: pytest"
