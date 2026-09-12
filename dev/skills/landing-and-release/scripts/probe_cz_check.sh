#!/usr/bin/env bash
# Probes the commitizen commit-shape validator with subjects that must be
# accepted and subjects that must be rejected, run from server/ as
# `uv run cz check --message "<subject>"`. cz check --rev-range only ever
# sees commits that already passed, so it cannot demonstrate a rejection --
# this probe is the validator check that actually exercises the reject path.
# See dev_plugin R01 landing-and-release, OBS-H findings 1-3.
set -euo pipefail

usage() {
    cat <<'EOF'
Usage: probe_cz_check.sh

Runs `uv run cz check --message "<subject>"` from server/ against a table of
subjects that must be accepted and subjects that must be rejected. Prints
each check as it runs and exits non-zero if any expectation is not met.

No arguments; no options besides --help/-h.
EOF
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi

repo_root="$(git rev-parse --show-toplevel)"
server_dir="${repo_root}/server"

echo "step: cd ${server_dir}"
cd "${server_dir}"

# Subjects that must pass cz check (accept).
accept_subjects=(
    "feat(search): add x"
    "release(colgrep-mcp): v0.1.2"
)

# Subjects that must fail cz check (reject): missing scope, trailing period,
# capitalised type, unknown type.
reject_subjects=(
    "feat: add x"
    "chore(repo): tidy."
    "Feat(search): add x"
    "style(server): x"
)

status=0

for subject in "${accept_subjects[@]}"; do
    echo "step: expect ACCEPT: uv run cz check --message \"${subject}\""
    if uv run cz check --message "${subject}" >/dev/null 2>&1; then
        echo "  ok"
    else
        echo "  FAIL: expected accept, cz check rejected: ${subject}" >&2
        status=1
    fi
done

for subject in "${reject_subjects[@]}"; do
    echo "step: expect REJECT: uv run cz check --message \"${subject}\""
    if uv run cz check --message "${subject}" >/dev/null 2>&1; then
        echo "  FAIL: expected reject, cz check accepted: ${subject}" >&2
        status=1
    else
        echo "  ok"
    fi
done

if [[ "${status}" -eq 0 ]]; then
    echo "probe_cz_check: all expectations met"
else
    echo "probe_cz_check: one or more expectations were not met" >&2
fi

exit "${status}"
