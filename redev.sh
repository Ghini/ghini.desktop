#!/bin/bash

git branch --unset-upstream
git push origin ghini-1.0-dev 
./scripts/bump_version.py +
