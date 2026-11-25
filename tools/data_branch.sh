#!/usr/bin/env bash
# Check out, or save, the "data" branch into the ./data folder.
#   tools/data_branch.sh open            fetch the branch (creates it empty the first time)
#   tools/data_branch.sh save "message"  commit and push only if something changed
# A save that cannot be pushed fails loudly (exit 1); it never reports success.
set -euo pipefail
case "$1" in
  open)
    if git ls-remote --exit-code --heads origin data >/dev/null 2>&1; then
      git fetch --quiet --depth=1 origin data
      git worktree add --quiet -B data data FETCH_HEAD
    else
      git worktree add --quiet --detach data
      (cd data && git checkout --quiet --orphan data && git rm -rfq . && echo "macro-hub data: history, state and logs. Written by the scheduled run." > README.md)
    fi
    ;;
  save)
    cd data
    git config user.name "macro-hub bot"
    git config user.email "actions@users.noreply.github.com"
    git add -A
    if git diff --cached --quiet; then
      echo "data: nothing changed, no commit"
      exit 0
    fi
    git commit --quiet -m "${2:-Update data}"
    for i in 1 2 3; do
      if git push --quiet origin HEAD:data; then
        echo "data: committed and pushed"
        exit 0
      fi
      echo "data: push attempt $i failed; fetching the branch and trying again"
      sleep $((i * 5))
      # someone else wrote the branch meanwhile: replay our commit on top of theirs
      git fetch --quiet --depth=1 origin data && git rebase --quiet FETCH_HEAD || git rebase --abort || true
    done
    echo "data: could NOT be saved after 3 attempts" >&2
    exit 1
    ;;
esac
