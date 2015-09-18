#!/bin/bash
# do not use --with-doctest as it's not used on coverall.io

nosetests --with-coverage --cover-package bauble --cover-html --cover-erase
