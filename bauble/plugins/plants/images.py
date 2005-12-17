#
# Images table definition
#

from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog


class Image(BaubleTable):

    # not unique but if a duplicate uri is entered the user
    # should be asked if this is what they want
    uri = StringCol()
    label = StringCol(length=50, default=None)
    
    # copyright ?
    # owner ?
    
    # should accessions also have a images in case an accession
    # differs from a plant slightly or should it just have a different
    # species
    #plant = MultipleJoin("Plantnames", joinColumn="image_id")
    species = ForeignKey('Species', cascade=True)
    
    
    def __str__(self): return self.label

#
# Image editor
#    
class ImageEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.image.columns"
    column_width_pref = "editor.image.column_width"
    default_visible_list = ['label', 'uri', 'species'] 
    
    label = 'Images'
    
    def __init__(self, parent=None, select=None, defaults={}):
        
        TreeViewEditorDialog.__init__(self, tables["Image"], 
                                            "Image Editor", parent,
                                            select=select, defaults=defaults)
        titles={"uri": "Location (URL)",
                 "label": "Label",
                 'speciesID': 'Plant Name'}
        self.columns.titles = titles