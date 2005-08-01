#
# Locations editor module
#

import locations
from tables import tables
from editors import editors
editors.register(locations.LocationsEditor, tables.Locations)