#!/bin/sh

# make sure we are in the project root dir
cd $(dirname $0)/..

# LINE is hard-coded and committed
# PUBLISHING is in the form 1.0.x
#
LINE=ghini-1.0
PUBLISHING=$(grep :bump bauble/version.py | grep -o '[1-9]\.[0-9]\.[0-9]*')

# let's check what Debian says first
python setup.py sdist | awk 'BEGIN{count=0}/^.*$/{count++; printf("running setup sdist: %d\r", count)}END{printf("\r\n")}'
cp dist/ghini.desktop-${PUBLISHING}.tar.gz /tmp/ghini.desktop-${PUBLISHING}.orig.tar.gz
( cd /tmp
  rm -fr ghini.desktop-${PUBLISHING}/ 2>/dev/null
  tar zxf ghini.desktop-${PUBLISHING}.orig.tar.gz 
  cd ghini.desktop-${PUBLISHING}/
  dh_make --yes --indep --file ../ghini.desktop-${PUBLISHING}.orig.tar.gz )
cp debian/* /tmp/ghini.desktop-${PUBLISHING}/debian
( cd /tmp/ghini.desktop-${PUBLISHING}/
  find debian -iname "*.ex" -execdir rm {} \; -or -name "*.source" -execdir rm {} \; -or -name "*~" -execdir rm {} \;
  debuild )

# all done for debian, publishing may follow, manually.

# make sure you have locally all remote branches
#
git remote update

# publish on github
#
git checkout $LINE
git merge $LINE-dev --no-edit -m "Merge branch 'ghini-1.0-dev' into ghini-1.0, as $PUBLISHING"
git push

# some day also produce a windows installable

# get back to work, and bump counters
#
git checkout $LINE-dev
git fetch --all
tmpfile=$(mktemp /tmp/bump-commit.XXXXXX)
scripts/bump_version.py + | tee $tmpfile
$(tail -n 1 $tmpfile)
git push

echo '******************************************************'
echo 'consider the following debian and pypi publishing steps'
echo
echo 'dput mentors $(ls /tmp/ghini.desktop_${PUBLISHING}-*_*.changes | tail -n 1)'
echo 'git checkout $LINE && python setup.py sdist --formats zip upload -r pypi'
