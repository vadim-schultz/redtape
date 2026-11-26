---
name: Chapter C8 - Release
overview: "The release chapter opens one pull request from the loop branch into main, and it tags the release after remote CI passes."
id: C8
depends_on: [C1, C2, C3, C4, C5, C6, C7]
touches: []
execution: chief-of-staff
isProject: false
---

# C8 - Release

**Depends on:** C1, C2, C3, C4, C5, C6, C7 · **Architecture:** [00-architecture.md](../00-architecture.md) · **Rollout:** [01-rollout.md](../01-rollout.md)

## Goal

The release branch, `main`, holds the whole work package after this chapter. One pull request from the loop branch, `feat/plans-discovery-admin-flow`, into `main` runs remote CI. A tag on the merged commit starts the release workflow.

## Read first

- [01-rollout.md](../01-rollout.md): the per-chapter gate and the final gate.
- The chief-of-staff git model, sections Local gate and Release. The local gate is defined there and only there.
- The chief-of-staff host workflow, section Release pull request.

## Coordination scope

**Add:**

- None.

**Edit:**

- None. The chief of staff records the result in the run ledger.

**Do not edit:**

- Every chapter file and every chapter branch. Each chapter is integrated before this chapter runs.

## Work items

The chief of staff runs every step, from the repository root. No implementer runs this chapter.

1. Confirm that every chapter row in the run ledger shows `done`, and that the final gate in the rollout holds.
2. Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`. Confirm that its working tree is clean.
3. Run the local gate on the loop branch head with `./ci.sh all`. Record `local gate: ./ci.sh all @ <sha>` in the run ledger. Stop when it fails.
4. Push the loop branch with `git push -u origin feat/plans-discovery-admin-flow`. This is the first push of the work package.
5. Open the pull request into `main` with `gh pr create --base main --head feat/plans-discovery-admin-flow --title "feat(discovery-admin): make the flow page the only discovery admin view" --body "<body>"`. The body states the removed routes, the added flow fields and the flag-only language menu. It ends with the line `🤖 Generated with [Claude Code](https://claude.com/claude-code)`.
6. Watch the remote checks with `gh pr checks --watch`. This is the remote run.
7. Merge the pull request with `gh pr merge --merge`, without `--delete-branch`. Then run `git checkout main && git pull`.
8. Tag the release with `git tag -a v<VERSION> -m "v<VERSION>"` and push it with `git push origin v<VERSION>`. The tag starts the release workflow.

If remote CI fails:

1. Reproduce the failure locally with the command that the failed check ran.
2. Fix it on the loop branch.
3. Rerun the local gate and record the new `local gate` line.
4. Push the loop branch. This is the second remote run.
5. Ask the user before a third remote run. Push nothing until the user answers.

## Tests or document checks

| Check | Happy path | Negative path |
| --- | --- | --- |
| Local gate | `./ci.sh all` exits 0 on the loop branch head | The gate fails. Stop before the push. Nothing is pushed or tagged. |
| Final grep | The removed-route grep of the rollout prints nothing | The grep prints a match. Return the match to the owning chapter. |
| Remote CI | `gh pr checks --watch` reports every check as passed before the merge | A check fails. Follow the remote-failure steps in Work items. |

## Review gate

- Every chapter row in the run ledger shows `done`, and the local gate is recorded on the loop branch head.
- The pull request base is `main`, and its head is the loop branch.
- The pull request body names the removed routes and the flow fields.

## Out of scope

- Any code change. A failing check returns to the owning chapter.
- Any change to the release branch other than the merge of the pull request.

## Verification

```bash
# Run from the repository root, on the loop branch head.
./ci.sh all
grep -rIn --exclude-dir=node_modules --exclude-dir=.venv \
  -E "admin/discovery/(catalogue|coverage|tasks|documents|pipeline)|discovery/admin/(tasks|catalogue|coverage|candidates|budgets)|admin/translations" \
  apps docs render.yaml | grep -v "docs/operations/loops/" || echo "no matches"
```

Expected: `./ci.sh all` exits 0. The `grep` prints no match, and the script prints `no matches`.

## Refactor report

_Not applicable. This chapter changes no code. The run ledger records the local gate and the remote result._

## Git workflow

- Check out the loop branch with `git checkout feat/plans-discovery-admin-flow`. Confirm that the working tree is clean.
- Run the local gate on the loop branch head with `./ci.sh all`. Record the result in the run ledger.
- Push the loop branch with `git push -u origin feat/plans-discovery-admin-flow`.
- Open the pull request with the `gh` command in Work items, and watch its checks with `gh pr checks --watch`.
- Merge with `gh pr merge --merge`, without `--delete-branch`. Tag only after the merge.
