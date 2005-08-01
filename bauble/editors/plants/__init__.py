#
# Plantnames editor module
#

import plants
from tables import tables
from editors import editors
editors.register(plants.PlantsEditor, tables.Plants)