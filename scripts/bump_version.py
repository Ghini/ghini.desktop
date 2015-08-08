#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2004-2010 Brett Adams <brett@bauble.io>
# Copyright 2015 Mario Frasca <mario@anche.no>.
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.

"""
Replace the version string in the relevant files.
"""

import os
import re
import sys

usage = """Usage: %s [<version> | + | ++]
""" % os.path.basename(sys.argv[0])


def root_of_clone():
    this_script = os.path.realpath(__file__)
    parts = this_script.split(os.path.sep)
    return os.path.sep + os.path.join(*parts[:-2])


def usage_and_exit(msg=None):
    print >>sys.stderr, usage
    if msg:
        print >>sys.stderr, msg
    sys.exit(1)

if len(sys.argv) != 2:
    usage_and_exit()
version = sys.argv[1]

bump_tag = ':bump'

# should I just increment version as of bauble.version?
if version in ['+', '++', '+++']:
    inc_patch = version == '+'
    inc_minor = version == '++'
    inc_major = version == '+++'
    rx = re.compile("^version\s*=\s*(?:\'|\")(.*)\.(.*)\.(.*)(?:\'|\").*%s.*$"
                    % bump_tag)

    matches = [rx.match(l).groups()
               for l in open(
                   os.path.join(root_of_clone(), "bauble/version.py"),
                   'r')
               if rx.match(l)]
    if matches:
        major, minor, patch = [int(i) for i in matches[0]]
        if inc_major:
            major += 1
            minor = 0
            patch = 0
        elif inc_minor:
            minor += 1
            patch = 0
        elif inc_patch:
            patch += 1
        version = "%s.%s.%s" % (major, minor, patch)

if not re.match('.*?\..*?\..*?', version):
    usage_and_exit('bad version string')


def bump_file(filename, rx):
    """
    rx is either a compiled regular expression or a string that can be
    compiled into one.  rx should have two groups, everything before the
    version and everything after the version.
    """

    # TODO; make sure that there is only one instance of
    # version=some_version in a file...don't have to if we can add
    # :bump somewhere in the comment on the same line
    if isinstance(rx, basestring):
        rx = re.compile(rx)

    from StringIO import StringIO
    buf = StringIO()
    for line in open(filename, 'r'):
        match = rx.match(line)
        if match:
            s = rx.sub(r'\1%s\2', line)
            line = s % version
            print ('%s: %s' % (filename, line)).strip()
        buf.write(line)

    f = open(filename, 'w')
    f.write(buf.getvalue())
    buf.close()


def bump_py_file(filename, varname='version'):
    """
    bump python files
    """

    rx = "^(%s\s*=\s*(?:\'|\")).*((?:\'|\").*%s.*)$" % (varname, bump_tag)
    bump_file(filename, rx)


def bump_desktop_file(filename):
    """
    bump xdf .desktop files
    """
    rx = "(^Version=).*?\..*?\..*?(\s+?.*?%s.*?$)" % bump_tag
    bump_file(filename, rx)


def bump_nsi_file(filename):
    """
    bump NSIS installer files
    """
    rx = '(^!define version ").*?\..*?\..*?(".*?%s.*?$)' % bump_tag
    bump_file(filename, rx)

# bump and grind
bump_py_file(os.path.join(root_of_clone(), 'bauble/version.py'))
bump_py_file(os.path.join(root_of_clone(), 'doc/conf.py'), 'release')
bump_desktop_file(os.path.join(root_of_clone(), 'data/bauble.desktop'))
bump_nsi_file(os.path.join(root_of_clone(), 'scripts/build.nsi'))

# TODO: the bauble UBC version is prefixed with ubc-
rx = "(^VERSION=\").*?\..*?\..*?(\".*?%s.*?$)" % bump_tag
bump_file(os.path.join(root_of_clone(), 'packages/builddeb.sh'), rx)

# TODO: commit the changes
print
print 'git commit -m "bumping to %s" bauble/version.py doc/conf.py'\
    ' data/bauble.desktop scripts/build.nsi packages/builddeb.sh' % version
