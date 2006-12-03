#
# merge-from-trunk
#
# Description: This script will update the current working copy from a revision
# on the trunk
#
# TODO: use HEAD by default
#

trunk_repo='https://forgesvn1.novell.com/svn/bauble/trunk'

#
# merge-from-trunk
#

from optparse import OptionParser

parser = OptionParser()

parser.add_option("-f", '--from_revision', dest="from_revision",
                  help="the revision to start with", metavar="REVISION")
parser.add_option("-t", '--to_revision', dest="to_revision",
                  help="the revision to start with", default='HEAD',
                  metavar="REVISION")

(options, args) = parser.parse_args()
print options.from_revision

msg = 'This script will update the current working copy from HEAD on the '\
      'trunk. \nPress any key to continue...'
raw_input(msg)


# TODO: should i....
# if to_revision != 'HEAD'
# make sure the that int(from_revision) < int(to_revision)
try:
    from_revision = int(options.from_revision)
    to_revision = options.to_revision
    if options.to_revision != 'HEAD':
        int(to_revision)
        
except:
    parser.error('the revision arg has to be an integer')
    
svn_cmd = 'svn merge -r %s:%s %s' % (from_revision, to_revision, trunk_repo)
print svn_cmd