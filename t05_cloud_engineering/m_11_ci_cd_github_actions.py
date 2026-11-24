# CI/CD with GitHub Actions
"""
CI (continuous integration): every push is built, linted and tested automatically, so
broken code is caught before merge. CD (continuous delivery/deployment): passing code on the
main branch is released automatically (or with one approval click).

GitHub Actions runs YAML WORKFLOWS stored in `.github/workflows/`. The example for this
lesson is `ci/ci.yml` (read it; this lesson parses it as plain text and explains it).

Anatomy
    name: ci                         display name
    on:                              TRIGGERS: push, pull_request, schedule, workflow_dispatch...
    permissions:                     what the auto-generated GITHUB_TOKEN may do (default LEAST)
    concurrency:                     cancel superseded runs
    jobs:                            run in parallel unless `needs:` orders them
      <job>:
        runs-on: ubuntu-latest       the runner machine (fresh VM every time)
        steps:                       run in order, sharing the checkout/filesystem
          - uses: owner/action@ref   reuse a published action (checkout, setup-uv...)
          - run: shell command       a non-zero exit code fails the step and the job
Expressions `${{ ... }}` read contexts (`github.ref`, `secrets.X`, `vars.X`, `env.X`).

This repo's pipeline: check out -> `astral-sh/setup-uv` (installs uv, Python 3.15 and caches
dependencies keyed on `uv.lock`) -> `uv sync --all-groups` -> `uv run ruff check .` ->
`SOLUTIONS=1 uv run pytest`. The same commands you run locally, which is the golden rule:
CI should only automate what already works on a laptop.

Deploy without long-lived keys: OIDC
Instead of storing AWS keys in GitHub secrets, the job gets a short-lived OIDC identity token
from GitHub (`permissions: id-token: write`). AWS trusts GitHub as an identity provider; an
IAM role's TRUST POLICY says "only repo X, branch main may assume me", and
`aws-actions/configure-aws-credentials` swaps the token for temporary credentials (m_01).
GCP does the same with Workload Identity Federation. Result: nothing to leak or rotate.

Typical pipeline: PR -> lint + test (+ build image, scan) -> merge -> build and push image to
a registry tagged with the git SHA -> deploy to staging -> smoke test -> approval -> prod.

Common mistakes
- Storing cloud access keys in repository secrets (use OIDC); printing secrets in logs.
- Overbroad `permissions:` (or none, which can default to write-all in old repos).
- Third-party actions pinned to a moving branch (`@main`): a compromised release runs in your
  pipeline with your secrets. Pin to a version tag, ideally a full commit SHA.
- Running deploy jobs on `pull_request` from forks, or trusting PR titles in `run:` scripts
  (script injection via `${{ github.event.pull_request.title }}`).
- No `timeout-minutes` (a hung job burns minutes) and no dependency cache (slow runs).
- CI-only behaviour that cannot be reproduced locally.

Production notes
- Require the CI job to pass (branch protection) before merge; use environments with
  required reviewers for production deploys.
- The OIDC role trust policy must restrict `sub` (repo, branch/environment): a wildcard
  lets any repo in your org assume it.
- Keep the deploy role least-privilege: it should only be able to deploy this service.
- Add Dependabot/Renovate for actions and dependencies; scan images (Trivy) and code (CodeQL).

Cost notes
- GitHub-hosted runners: public repos are free; private repos include a monthly quota
  (e.g. 2,000 Linux minutes on Free), then per-minute billing (macOS minutes cost ~10x).
- Caching and `concurrency: cancel-in-progress` directly cut your bill.
"""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent / "ci" / "ci.yml"


def top_level_keys(text: str) -> list[str]:
    return [
        m.group(1) for line in text.splitlines() if (m := re.match(r"^([A-Za-z_][\w-]*):", line))
    ]


def job_names(text: str) -> list[str]:
    names, in_jobs = [], False
    for line in text.splitlines():
        if re.match(r"^[A-Za-z_]", line):
            in_jobs = line.startswith("jobs:")
        elif in_jobs and (m := re.match(r"^  ([\w-]+):\s*$", line)):
            names.append(m.group(1))
    return names


def uses_actions(text: str) -> list[str]:
    return re.findall(r"^\s*-?\s*uses:\s*(\S+)", text, flags=re.MULTILINE)


def run_commands(text: str) -> list[str]:
    """Single-line `run: cmd` values and `run: |` block lines, in file order."""
    commands: list[str] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = re.match(r"^(\s*)(?:-\s+)?run:\s*(.*)$", lines[i])
        i += 1
        if not m:
            continue
        indent, rest = len(m.group(1)), m.group(2).strip()
        if rest in ("|", ">", "|-", ">-"):
            while i < len(lines) and (
                not lines[i].strip() or len(lines[i]) - len(lines[i].lstrip()) > indent
            ):
                if lines[i].strip():
                    commands.append(lines[i].strip())
                i += 1
        elif rest:
            commands.append(rest)
    return commands


def find_unpinned_actions(text: str) -> list[str]:
    """Actions without a version, or pinned to a moving branch like @main."""
    risky = []
    for ref in uses_actions(text):
        if ref.startswith(("./", "docker://")):
            continue
        _, _, version = ref.partition("@")
        if version in ("", "main", "master", "latest", "HEAD"):
            risky.append(ref)
    return risky


def uses_static_aws_keys(text: str) -> bool:
    return bool(re.search(r"secrets\.AWS_(ACCESS_KEY_ID|SECRET_ACCESS_KEY)", text))


if __name__ == "__main__":
    text = WORKFLOW.read_text()
    print("top-level keys:", top_level_keys(text))
    print("jobs:", job_names(text))
    print("actions used:", uses_actions(text))
    print("run commands:", run_commands(text))
    print("unpinned actions:", find_unpinned_actions(text))
    print("static AWS keys in use:", uses_static_aws_keys(text))
    print("uses OIDC:", "id-token: write" in text)

    risky = "steps:\n  - uses: some/tool@main\n  - run: echo ${{ secrets.AWS_ACCESS_KEY_ID }}\n"
    print("risky sample:", find_unpinned_actions(risky), uses_static_aws_keys(risky))
