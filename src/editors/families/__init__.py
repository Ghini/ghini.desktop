#
# Families editor module
#

name = 'Families'
description = 'Families'
depends = ("tables.families") # tables.families the module not the table

import families
editor = families.FamiliesEditor