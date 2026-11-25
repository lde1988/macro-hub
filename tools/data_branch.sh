#!/usr/bin/env bash
# Check out, or save, the "data" branch into the ./data folder.
#   tools/data_branch.sh open            fetch the branch (creates it empty only if it truly does not exist)
#   tools/data_branch.sh save "message"  commit and push only if something changed
# A save that cannot be pushed fails loudly (exit 1); it never reports success.
set -uo pipefail
case "$1" in
  open)
    git ls-remote --exit-code --heads origin data >/dev/null 2>&1
    rc=$?
    if [ "$rc" -eq 0 ]; then
      git fetch --quiet --depth=1 origin data || exit 1
      git worktree add --quiet -B data data FETCH_HEAD || exit 1
    elif [ "$rc" -eq 2 ]; then          # 2 = the remote answered and has no such branch: first ever run
      git worktree add --quiet --detach data || exit 1
      (cd data && git checkout --quiet --orphan data && git rm -rfq . && echo "macro-hub data: history, state and logs. Written by the scheduled run." > README.md) || exit 1
    else                                 # any other answer is a network or access problem: never start from empty
      echo "data: could not reach the repository to read the data branch (git exit $rc)" >&2
      exit 1
    fi
    ;;
  save)
    cd data || exit 1
    git config user.name "macro-hub bot"
    git config user.email "actions@users.noreply.github.com"
    git add -A
    if git diff --cached --quiet; then
      echo "data: nothing changed, no commit"
      exit 0
    fi
    git commit --quiet -m "${2:-Update data}" || exit 1
    for i in 1 2 3; do
      if git push --quiet origin HEAD:data; then
        echo "data: committed and pushed"
        exit 0
      fi
      echo "data: push attempt $i failed; fetching the branch and trying again"
      sleep $((i * 5))
      # If another writer moved the branch, replay our commit on top of theirs. The checkout is shallow,
      # so fetch enough history for git to find the common starting point first.
      if git fetch --quiet --depth=50 origin data; then
        git rebase --quiet FETCH_HEAD >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1 || true
      fi
    done
    echo "data: could NOT be saved after 3 attempts" >&2
    exit 1
    ;;
esac
