#
# merge-to-trunk
#
# Description: this merges the changes a branch into the current working copy
#

trunk_repo='https://forgesvn1.novell.com/svn/bauble/trunk'

branch_root='https://forgesvn1.novell.com/svn/bauble/branches/'



from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", '--from_revision', dest="from_revision", type='int',
                  help="start of merge range", metavar="REVISION")
parser.add_option("-t", '--to_revision', dest="to_revision", type='int',
                  help="the end of the merge range", metavar="REVISION")
parser.add_option("-b", '--branch', dest="branch",
                  help="the branch to merge to", metavar="BRANCH")

(options, args) = parser.parse_args()
print options.from_revision

msg = 'This script will merge changes from a branch into the current working '\
      'copy. \nPress any key to continue...'
raw_input(msg)

if not options.from_revision or not options.branch or not options.to_revision:
    parser.error('no options supplied, try merge-to-trunk.py -h to see the help')
    

# make sure the that int(from_revision) < int(to_revision)
try:
    from_revision = int(options.from_revision)
    to_revision = int(options.to_revision)
except:
    parser.error('the revision arguments has to be an integer')
    
svn_cmd = 'svn merge -r %s:%s %s%s' % (from_revision, to_revision, 
                                       branch_root, options.branch)
print svn_cmd