#
# Genera editor module
#

import genera
from tables import tables
from editors import editors
editors.register(genera.GeneraEditor, tables.Genera)