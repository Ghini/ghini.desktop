#
# Families editor module
#

depends = ("tables.family") # tables.families the module not the table

from tables import tables
import editors
import families
editors.editors.register(families.FamiliesEditor, tables.Family)