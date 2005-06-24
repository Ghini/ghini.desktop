#
# GBIF view
#

label = "GBIF"
description = 'GBIF'

try:
    import gbif
except ImportError, e:
    # TODO: print to the log somewhere that the gbif view could
    # not be loaded
    print e
    print "Could not load GBIFView."
else:
    view = gbif.GBIFView