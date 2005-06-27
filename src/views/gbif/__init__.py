#
# GBIF view
#

# **********
# i don't really think this should be provided as a standalone view but
# rather a tool to query the GBIF database, unless we wanted to make a 
# standalone client for GBIF but then you could just go the gbif.net
# *********

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
    pass
    #view = gbif.GBIFView