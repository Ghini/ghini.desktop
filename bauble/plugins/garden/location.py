#
# Locations table definition
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.editor import TreeViewEditorDialog


class Location(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
	defaultOrder = 'site'

    # should only need either loc_id or site as long as whichever one is 
    # unique, probably site, there is already and internal id
    # what about sublocations, like if the locations were the grounds
    # and the sublocation is the block number
    #loc_id = StringCol(length=20) 
    site = StringCol(length=60, alternateID=True)
    description = StringCol(default=None)

    plants = MultipleJoin("Plant", joinColumn="location_id")
    
    def __str__(self): 
        return self.site

#
# Location Editor
#
class LocationEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.location.columns"
    column_width_pref = "editor.location.column_width"
    default_visible_list = ['site', 'description'] 

    label = 'Location'

    def __init__(self, parent=None, select=None, defaults={}):
        TreeViewEditorDialog.__init__(self, Location, "Location Editor", 
                                      parent,select=select, defaults=defaults)
        # set headers
        titles = {"site": "Site",
                  "description": "Description"}
        self.columns.titles = titles
