#!/usr/bin/env bash
# Rebases a task branch onto its target, re-runs the gates, and merges with
# --no-ff. Never pushes. See dev_plugin R01 landing-and-release and the
# machine-level writing-history skill for the general rebase-then-merge
# method this codifies for this repository's specific gates.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: land_branch.sh <task-branch> <target-branch> <merge-message>

Rebases <task-branch> onto <target-branch>, runs this repository's gates
(pytest, ruff check, ruff format --check, cz check --rev-range) against the
rebased branch, then merges <task-branch> into <target-branch> with
`git merge --no-ff -m "<merge-message>"`. Afterwards searches the merged tree
for leftover conflict markers and fails if any remain.

All three arguments are mandatory; <merge-message> is the merge commit
message (name the unit of work it integrates). Requires a clean working tree.
Never pushes anything.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

if [[ $# -lt 3 ]]; then
    echo "error: land_branch.sh requires <task-branch> <target-branch> <merge-message>" >&2
    usage >&2
    exit 1
fi

task_branch="$1"
target_branch="$2"
merge_message="$3"

repo_root="$(git rev-parse --show-toplevel)"
cd "${repo_root}"

echo "step: verify branches exist: ${task_branch}, ${target_branch}"
if ! git rev-parse --verify "${task_branch}" >/dev/null 2>&1; then
    echo "error: no such branch: ${task_branch}" >&2
    exit 1
fi
if ! git rev-parse --verify "${target_branch}" >/dev/null 2>&1; then
    echo "error: no such branch: ${target_branch}" >&2
    exit 1
fi

echo "step: probe the merge message with cz check --message (merge commits are commits too)"
(cd "${repo_root}/server" && uv run cz check --message "${merge_message}")

echo "step: check the working tree is clean"
if [[ -n "$(git status --porcelain)" ]]; then
    echo "error: working tree is not clean; commit or set changes aside first (never bare 'git stash')" >&2
    exit 1
fi

echo "step: git checkout ${task_branch}"
git checkout "${task_branch}"

echo "step: git rebase ${target_branch}"
git rebase "${target_branch}"

echo "step: cd server && uv run pytest -q"
(cd "${repo_root}/server" && uv run pytest -q)

echo "step: cd server && uv run ruff check"
(cd "${repo_root}/server" && uv run ruff check)

echo "step: cd server && uv run ruff format --check"
(cd "${repo_root}/server" && uv run ruff format --check)

echo "step: cd server && uv run cz check --rev-range ${target_branch}..${task_branch}"
(cd "${repo_root}/server" && uv run cz check --rev-range "${target_branch}..${task_branch}")

echo "step: git checkout ${target_branch}"
git checkout "${target_branch}"

echo "step: git merge --no-ff -m \"${merge_message}\" ${task_branch}"
git merge --no-ff -m "${merge_message}" "${task_branch}"

echo "step: search the merged tree for conflict markers"
if git grep -n '<<<<<<<' -- . >/dev/null 2>&1; then
    echo "error: conflict markers remain after merge; resolve them before proceeding" >&2
    git grep -n '<<<<<<<' -- . >&2 || true
    exit 1
fi

echo "land_branch: merged ${task_branch} into ${target_branch}; nothing pushed"
