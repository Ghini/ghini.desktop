#
# Plantnames editor module
#

import plantnames
from tables import tables
from editors import editors
editors.register(plantnames.PlantnamesEditor, tables.Plantnames)