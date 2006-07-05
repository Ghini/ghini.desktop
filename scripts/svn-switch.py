#!/usr/bin/env python

import os

repo_root='https://forgesvn1.novell.com/svn/bauble/'

from optparse import OptionParser
parser = OptionParser()
options, args = parser.parse_args()

if len(args) != 1:
    parser.error('need to provide a path in the repository')

repo = '%s%s' % (repo_root, args[0])
svn_cmd = 'svn switch %s' % repo

response = raw_input('Do you want to switch to %s? ' % repo)
if response in ('Y', 'y'):
    print svn_cmd
    os.system(svn_cmd)
