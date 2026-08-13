#!/bin/sh
#
# "publishing to production" - see doc/building.rst.
#
# This script only does the git choreography that has to happen by
# hand: merging ghini-3.1-dev into ghini-3.1, then tagging the result.
# Pushing that tag is the trigger - .github/workflows/publish-pypi.yml
# and docker-release.yml take it from there (build, publish to PyPI
# via Trusted Publishing, publish the Docker image, then bump
# ghini-3.1-dev to the next version). This script does not build or
# upload anything itself, to avoid racing those workflows.

set -e

# make sure we are in the project root dir
cd "$(dirname "$0")/.."

# LINE is hard-coded and committed
LINE=ghini-3.1

# PUBLISHING is in the form 3.1.x - it's already the *next* version to
# release, because the previous run of this same sequence left it
# bumped forward, ready for this one.
PUBLISHING=$(grep :bump bauble/_version.py | grep -o '[1-9]\.[0-9]\.[0-9]*')

# make sure you have locally all remote branches
git remote update

# merge the development line into the production line
git checkout "$LINE"
git merge "$LINE-dev" --no-edit -m "Merge branch '$LINE-dev' into $LINE, as $PUBLISHING"
git push

# tag the merge commit itself, and only now - tagging before the merge
# (or merging after tagging) leaves the tag pointing at the wrong
# commit, and setuptools_scm reports a dirty .postN+g<hash> version.
git tag "v$PUBLISHING"
git push origin "v$PUBLISHING"

echo "pushed v$PUBLISHING to $LINE - Actions will take it from here."

# back to the corresponding dev branch.
git checkout "$LINE-dev"

# prepare for the next publish: bump ghini-3.1-dev's version files
# forward. this belongs here, not in publish-pypi.yml - it's part of
# "publish", not part of any of the triggered publishing action, and
# doesn't depend on any one downstream artifact's success or failure.
tmpfile=$(mktemp)
scripts/bump_version.py + | tee "$tmpfile"
# bump_version.py's own last line of output is a ready-to-run
# `git commit -m "bumping_to_X.Y.Z" ...` - reuse it verbatim so the
# commit message stays exactly the same shape it always has.
eval "$(tail -n 1 "$tmpfile")"
git push
 
