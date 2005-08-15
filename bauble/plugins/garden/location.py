#
# Locations table definition
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog


class Location(BaubleTable):

    # should only need either loc_id or site as long as whichever one is 
    # unique, probably site, there is already and internal id
    # what about sublocations, like if the locations were the grounds
    # and the sublocation is the block number
    #loc_id = StringCol(length=20) 
    site = StringCol(length=60, unique=True)
    description = StringCol(default=None)

    plants = MultipleJoin("Plants", joinColumn="location_id")
    #plant = ForeignKey('Plants', notNull=True)
    
    def __str__(self): return self.site

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
        headers={"site": "Site",
                 "description": "Description"}
        self.column_meta.headers = headers