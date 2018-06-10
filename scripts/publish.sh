#!/bin/sh

# make sure we are in the project root dir
cd $(dirname $0)/..

# let's check what Debian says first
python setup.py sdist | awk 'BEGIN{count=0}/^.*$/{count++; printf("running setup sdist: %d\r", count)}END{printf("\r\n")}'
# debian needs a frozen upstream, on which to base its packaging.  a good
# way to freeze might mean starting a branch at the merge point.

# LINE is hard-coded and committed
# PUBLISHING is in the form 3.1.x
#
LINE=ghini-3.1
PUBLISHING=$(grep :bump bauble/version.py | grep -o '[1-9]\.[0-9]\.[0-9]*')

# make sure you have locally all remote branches
#
git remote update

# publish on github
#
git checkout $LINE
git merge $LINE-dev --no-edit -m "Merge branch 'ghini-3.1-dev' into ghini-3.1, as $PUBLISHING"
git push

# publish on pypi
#
echo git checkout ghini-3.1 && python setup.py sdist --formats zip upload -r pypi

# some day also produce a windows installable

# get back to work, and bump counters
#
git checkout $LINE-dev
git fetch --all
tmpfile=$(mktemp /tmp/bump-commit.XXXXXX)
scripts/bump_version.py + | tee $tmpfile
$(tail -n 1 $tmpfile)
git push
