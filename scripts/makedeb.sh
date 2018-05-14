#!/bin/bash
# make sure we are in the project root dir
cd $(dirname $0)/..

# grab version from desktop file
VERSION=$(sed -ne 's/Version=[^0-9]*\([0-9\.]*\).*/\1/p' data/ghini.desktop)
DIRNAME=bauble-$VERSION

# make sure target dir is clean
rm -fr $DIRNAME 2>/dev/null

# copy template to target dir
cp -a package-template $DIRNAME
# remove placeholders, needed for storing directory structure in git, 
find $DIRNAME -name ".placeholder" -exec rm {} \;
# set version in control file
sed -i 's/VERSION/'$VERSION'/g' $DIRNAME/DEBIAN/control

# copy current files to target dir
cp -a src/* $DIRNAME/
cp -a build/lib*/bauble $DIRNAME/usr/lib/python2.7/dist-packages/
cp -a build/share/* $DIRNAME/usr/share/
cp -a ./scripts/ghini $DIRNAME/usr/bin/

# don't distribute emacs backup files
find $DIRNAME -name "*~" -exec rm {} \;

# HERE we make the deb file - files inside deb must be owned by root
fakeroot bash -c 'chown -R root.root bauble-'$VERSION'; dpkg -b bauble-'$VERSION

# target dir is really a temporary dir, so remove it now
rm -fr $DIRNAME 2>/dev/null
