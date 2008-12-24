#!/usr/bin/env python
# TODO: change all the relative version strings to the version passed
# as an argument

import os
import re
import sys

usage = """Usage: %s <version>
""" % os.path.basename(sys.argv[0])

def usage_and_exit(msg=None):
    print >>sys.stderr, usage
    if msg:
        print >>sys.stderr, msg
    sys.exit(1)

if len(sys.argv) != 2:
    usage_and_exit()
version = sys.argv[1]

if not re.match('.*?\..*?\..*?', version):
    usage_and_exit('bad version string')

bump_tag = ':bump'

def bump_file(filename, rx):
    """
    rx should have two groups, everything before the version and
    everything after the version
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
            print '%s: %s' % (filename, line)
        buf.write(line)

    return
    f = open(filename, 'w')
    f.write(buf.getvalue())
    buf.close()

def bump_py_file(filename):
    rx = "(^version\s*?=\s*?\'|\").*?\..*?\..*?(\'|\".*?%s.*?$)" % bump_tag
    bump_file(filename, rx)

def bump_desktop_file(filename):
    rx = "(^Version=).*?\..*?\..*?(\s+?.*?%s.*?$)" % bump_tag
    bump_file(filename, rx)

def bump_nsi_file(filename):
    rx = '(^!define version ").*?\..*?\..*?(".*?%s.*?$)' % bump_tag
    bump_file(filename, rx)

# bump and grind
bump_py_file('setup.py')
bump_py_file('bauble/__init__.py')
bump_desktop_file('data/bauble.desktop')
bump_nsi_file('scripts/build.nsi')

