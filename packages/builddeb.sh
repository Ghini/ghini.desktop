# branch this directory and create a source dist
TOPLEVEL=`pwd`
VERSION="ubc-1.0.0b2"
TARBALL="bauble-$VERSION.tar.gz"
ORIG_TARBALL="bauble_$VERSION.orig.tar.gz"

if [[ "$1" == "" ]] ; then
    echo "ERROR: what distribution?"
    exit 1
elif ! [ -d "$TOPLEVEL/packages/$1" ] ; then
    echo "package does not exist: $1"
    exit 1
else
    DIST="$1"
fi

run () {
    # run the first argument and check the return value
    eval "$1"    
    if [[ $? -eq  1 ]] ; then
	echo "ERROR: The following command did not succeed: "
	echo "$1"
	read -s -n1 -p "Would you like to continue? (y/n) " reply
	if [ "$reply" != 'y' ] ; then
	    echo
	    exit
	fi
    fi
}

make_tarball () {
    # create a sdist
    ! [ -d "dist" ] && run "mkdir dist"
    run "bzr checkout --lightweight . dist/deb"
    run "rm -fr dist/deb/.bzr"
    run "cd dist/deb"
    run "python setup.py sdist --format=gztar"
}

if [ -f "dist/deb/dist/$TARBALL" ] ; then
    read -s -n1 -p "Would you like to use the existing tarball? (y/n) " reply
    if [ "$reply" != 'y' ] ; then
	make_tarball
    else
	cd "dist/deb"
    fi
	
else
    make_tarball
fi


# copy the sdist to a deb orig tarball
run "cd dist"
run "cp $TARBALL $ORIG_TARBALL"

# debian the tarball
run "tar zxvf $TARBALL"
run "cd bauble-$VERSION"
if ! [ -d "debian" ] ; then
    run "mkdir debian"
fi
run "cp $TOPLEVEL/packages/$DIST/* debian"

# build the source package
run "debuild -S"
