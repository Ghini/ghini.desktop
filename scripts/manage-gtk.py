# rename gtk dir
# copy gtk to dist dir and run gdk-query-pixbuf-loaders

import os, sys

if sys.platform != 'win32':
    print('only for win32')
    sys.exit()

GTK_PATH = 'c:\\GTK'
GTK_OFF_PATH = 'c:\\GTK.off'

from optparse import OptionParser
parser = OptionParser()
(options, args) = parser.parse_args()

cmds = ('off', 'on', 'dist')

if len(args) < 1 or args[0] not in cmds:
    parser.error('expecting a command: %s' % str(cmds))

import shutil
if args[0] == 'off':
    if os.path.exists(GTK_OFF_PATH):
        print(('%s already exists' % GTK_OFF_PATH))
        sys.exit(1)
    else:
        shutil.move(GTK_PATH, GTK_OFF_PATH)
elif args[0] == 'on':
    if os.path.exists(GTK_PATH):
        print(('%s already exists' % GTK_PATH))
        sys.exit(1)
    else:
        shutil.move(GTK_OFF_PATH, GTK_PATH)
elif args[0] == 'dist':
    print('Error: not implemented')


