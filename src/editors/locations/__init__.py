#
# Locations editor module
#

label = 'Locations'
description = 'Locations'
depends = ("tables.Locations") # tables.locations the module not the table

import locations
editors = [locations.LocationsEditor]