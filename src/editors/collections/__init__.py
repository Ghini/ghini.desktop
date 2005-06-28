#
# Collections editor module
#

label = 'Collections'
description = 'Collections'
depends = ("tables.Collections") # tables.collections the module not the table

import collections
editor = collections.CollectionsEditor