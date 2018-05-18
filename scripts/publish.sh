#!/bin/sh
# make sure we are in the project root dir
cd $(dirname $0)/..

# LINE is hard-coded and committed
# PUBLISHING is in the form 1.0.x
#
LINE=ghini-1.0
PUBLISHING=$(grep :bump bauble/version.py | grep -o '[1-9]\.[0-9]\.[0-9]*')

# make sure you have locally all remote branches
#
git remote update

# publish on github
#
git checkout $LINE
git merge $LINE-dev --no-edit -m "Merge branch 'ghini-1.0-dev' into ghini-1.0, as $PUBLISHING"
git push

# publish on pypi
#
python setup.py sdist --formats zip upload -r pypi

# some day also produce a debian package

# some day also produce a windows installable

# get back to work, and bump counters
#
git checkout $LINE-dev
git fetch --all
tmpfile=$(mktemp /tmp/bump-commit.XXXXXX)
scripts/bump_version.py + | tee $tmpfile
$(tail -n 1 $tmpfile)
git push
