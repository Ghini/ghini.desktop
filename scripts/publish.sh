#!/bin/sh

# make sure we are in the project root dir
cd $(dirname $0)/..

# let's check what Debian says first
python setup.py sdist | awk 'BEGIN{count=0}/^.*$/{count++; printf("running setup sdist: %d\r", count)}END{printf("\r\n")}'
VERSION=$(ls dist/*.tar.gz | tail -n 1 | sed -ne 's/[^-]*-\(.*\).tar.gz/\1/p')
cp dist/ghini.desktop-${VERSION}.tar.gz /tmp/ghini.desktop-${VERSION}.orig.tar.gz
( cd /tmp
  rm -fr ghini.desktop-${VERSION}/ 2>/dev/null
  tar zxf ghini.desktop-${VERSION}.orig.tar.gz 
  cd ghini.desktop-${VERSION}/
  dh_make --yes --indep --file ../ghini.desktop-${VERSION}.orig.tar.gz )
cp debian/* /tmp/ghini.desktop-${VERSION}/debian
( cd /tmp/ghini.desktop-${VERSION}/
  find debian -iname "*.ex" -execdir rm {} \; -or -name "*.source" -execdir rm {} \; -or -name "*~" -execdir rm {} \;
  debuild )

# decide whether we continue
# in case, we should really dput the following to mentors.debian.org
echo "do we continue? (Ctrl-C to interrupt)"
read i
if [ "$i"!="skip" ]; then echo dput mentors $(ls /tmp/ghini.desktop_${VERSION}-*_*.changes | tail -n 1); fi

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
echo python setup.py sdist --formats zip upload -r pypi

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
