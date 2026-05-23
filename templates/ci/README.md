# Cortex CI plugin — workflow templates

Drop-in templates that wire the Pluggable Middle CI plugin (Phase 07)
into the most common providers.

## Files

| Template | Provider |
|---|---|
| `github-actions-cortex-validate.yml` | GitHub Actions (Level 1 validate + Level 2 PR comment). |
| `gitlab-ci-cortex-validate.yml` | GitLab CI (Level 1 validate + optional MR note). |

## How it works

1. The CI job runs `cortex ci validate-pr` against the PR diff.
2. Exit codes are passed through:
   * `0` = pass; the job is green.
   * `1` = warnings (scope drift, non-required hook failure); the job
     is yellow (you can drop `continue-on-error: true` if you prefer a
     hard fail).
   * `2` = blocked (required hook failed, no Session matched,
     unimplemented files in scope); the job is red.
   * `3` = error (git failure, missing diff, etc.); investigate.
3. Optionally, a second invocation with `--format pr-comment` produces
   a Markdown summary that is posted (or sticky-edited) on the PR.

## Customising the template

* If your project uses a different trunk branch, set `--base-branch`
  explicitly instead of relying on the provider's default.
* If you want to gate review sessions (Phase 07 Level 3), the workflow
  can chain `cortex ci open-review-session` →
  `cortex ci report-checkpoint` → `cortex ci close-review-session`
  around the validate step. See `docs/architecture/review-sessions.md`
  for the recommended layout.

## Troubleshooting

* "No Cortex Session matched this PR" — the contributor did not open
  a Cortex Session before pushing. Ask them to run
  `cortex create-spec ...` first (the session opens automatically).
* "spec declares no verification_hooks" — the spec is from before
  Phase 01; the validation is partial. Add at least one hook to the
  spec frontmatter (see `cortex create-spec --verification-hook`).
