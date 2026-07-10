@echo off
REM Enable this repo's git hooks (.githooks\) for your clone. Run once after cloning.
REM Git hooks in .git\hooks aren't shared; pointing core.hooksPath at the tracked
REM .githooks\ folder gives everyone the same pre-commit / pre-push gates.
git config core.hooksPath .githooks
echo Git hooks enabled (core.hooksPath = .githooks)
echo   pre-commit: ruff + tsc on staged files  ^|  pre-push: pytest
