#
# Locations table definition
#

from sqlobject import * 
from bauble.plugins import BaubleTable, tables
from bauble.treevieweditor import TreeViewEditorDialog

def edit_callback(row):
    value = row[0]    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = LocationEditor(select=[value], model=value)
    return e.start() != None


def add_plant_callback(row):
    from bauble.plugins.garden.plant import PlantEditor
    value = row[0]
    e = PlantEditor(defaults={'locationID': value})
    return e.start() != None


def remove_callback(row):    
    value = row[0]
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
        
    if utils.yes_no_dialog(msg):
        from sqlobject.main import SQLObjectIntegrityError
        try:
            value.destroySelf()
            # since we are doing everything in a transaction, commit it
            sqlhub.processConnection.commit() 
            return True
        except SQLObjectIntegrityError, e:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, str(e))
        except:
            msg = "Could not delete '%s'. It is probably because '%s' "\
                  "still has children that refer to it.  See the Details for "\
                  " more information." % (s, s)
            utils.message_details_dialog(msg, traceback.format_exc())


loc_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Add plant', add_plant_callback),
                    ('--', None),
                    ('Remove', remove_callback)]

class Location(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'site'

    # should only need either loc_id or site as long as whichever one is 
    # unique, probably site, there is already and internal id
    # what about sublocations, like if the locations were the grounds
    # and the sublocation is the block number
    #loc_id = StringCol(length=20) 
    site = UnicodeCol(length=60, alternateID=True)
    description = UnicodeCol(default=None)

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

    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
        TreeViewEditorDialog.__init__(self, Location, "Location Editor", 
                                      parent,select=select, defaults=defaults,
                                      **kwargs)
        # set headers
        titles = {"site": "Site",
                  "description": "Description"}
        self.columns.titles = titles
