#!/usr/bin/env bash
# Refuses to run anywhere but the main checkout, on main, with a clean tree.
# Prints the dry-run bump by default; with --run, executes the bump and test
# suite (never the push). See dev_plugin R01 landing-and-release, CONTRIBUTING.md.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: release.sh [--run]

Without --run: prints `cz bump --changelog --dry-run` output after the
main-checkout / main-branch / clean-tree checks pass. Does not mutate anything.

With --run: additionally executes `uv run cz bump --changelog` and
`uv run pytest` from server/, then prints the exact `git push origin main
v<x.y.z>` line to run by hand. It never runs that push itself.

Refuses unconditionally when the current directory is not the main checkout
(the first entry of `git worktree list`), or the current branch is not
`main`, or the working tree is not clean.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

run_mode=0
if [[ "${1:-}" == "--run" ]]; then
    run_mode=1
elif [[ $# -gt 0 ]]; then
    echo "error: unknown argument: $1" >&2
    usage >&2
    exit 1
fi

echo "step: check this is the main checkout"
toplevel="$(git rev-parse --show-toplevel)"
main_checkout="$(git worktree list | head -n1 | awk '{print $1}')"
if [[ "${toplevel}" != "${main_checkout}" ]]; then
    echo "refuse: this is '${toplevel}', not the main checkout '${main_checkout}'; a release only runs from the main checkout, never a scratch or detached worktree" >&2
    exit 1
fi

echo "step: check the current branch is main"
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "${current_branch}" != "main" ]]; then
    echo "refuse: current branch is '${current_branch}', not main" >&2
    exit 1
fi

echo "step: check the working tree is clean"
if [[ -n "$(git status --porcelain)" ]]; then
    echo "refuse: working tree is not clean" >&2
    exit 1
fi

echo "step: cd server && uv run cz bump --changelog --dry-run"
(cd "${toplevel}/server" && uv run cz bump --changelog --dry-run)

if [[ "${run_mode}" -eq 0 ]]; then
    echo "release.sh: dry-run only; re-run with --run to execute the bump (never the push)"
    exit 0
fi

echo "step: cd server && uv run cz bump --changelog"
(cd "${toplevel}/server" && uv run cz bump --changelog)

echo "step: cd server && uv run pytest"
(cd "${toplevel}/server" && uv run pytest)

new_version="$(cd "${toplevel}/server" && uv run python -c 'import colgrep_mcp; print(colgrep_mcp.__version__)')"
echo "release.sh: bump complete. Push by hand (this script never pushes):"
echo "  git push origin main v${new_version}"
echo "release.sh: pushing the tag runs .github/workflows/publish.yml — PyPI upload and GitHub release follow from it"
