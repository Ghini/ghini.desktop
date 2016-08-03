#!/bin/sh
git up
git checkout ghini-1.0
git merge ghini-1.0-dev
git commit -m "publish to 1.0"
git push
git checkout ghini-1.0-dev
git up
scripts/bump_version.py +
git commit -a -m "bumping version"
git push
