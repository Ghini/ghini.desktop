#!/bin/sh
LINE=ghini-1.0
#### the following lines make sure you have locally all remote branches
git remote update
PUBLISHING=$(grep :bump bauble/version.py | grep -o '[1-9]\.[0-9]\.[0-9]*')
git checkout $LINE
git merge $LINE-dev --no-edit -m "Merge branch 'ghini-1.0-dev' into ghini-1.0, as $PUBLISHING"
git push
git checkout $LINE-dev
git fetch --all
tmpfile=$(mktemp /tmp/bump-commit.XXXXXX)
scripts/bump_version.py + | tee $tmpfile
$(tail -n 1 $tmpfile)
# rm $tmpfile
git push
