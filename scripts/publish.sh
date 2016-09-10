#!/bin/sh
LINE=ghini-1.0
#### the following lines make sure you have locally all remote branches
# git branch -r |
#     grep -v '\->' |
#     while read remote
#     do
#         git branch --track "${remote#origin/}" "$remote" 2>/dev/null
#     done
git fetch --all
git checkout $LINE
git merge $LINE-dev
git commit -m "publish to 1.0"
git push
git checkout $LINE-dev
git fetch --all
scripts/bump_version.py +
git commit -a -m "bumping version"
git push
