#
# Locations editor module
#

name = 'Locations'
description = 'Locations'
depends = ("tables.Locations") # tables.locations the module not the table

import locations
editor = locations.LocationsEditor