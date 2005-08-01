#
# Families editor module
#

depends = ("tables.family") # tables.families the module not the table

from tables import tables
from editors import editors
import families
#editors = [families.FamiliesEditor]

editors.register(families.FamiliesEditor, tables.Family)