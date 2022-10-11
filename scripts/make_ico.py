#!/usr/bin/env python

import sys, os

if not sys.platform.startswith('linux'):
    print('This script only works on Linux.')
    sys.exit()

sizes = ('16x16', '32x32', '48x48')
image_src = 'bauble/images/icon.svg'
out_template = 'bauble/images/icon%s.png'
icon_filename = 'bauble/images/icon.ico'
convert = lambda size: os.system('convert %s -resize %s %s' % \
                                 (image_src, size, out_template % size))

for size in sizes:
    convert(size)

os.system('icotool -c %s -o %s' % \
          (' '.join([out_template % s for s in sizes]), icon_filename))


