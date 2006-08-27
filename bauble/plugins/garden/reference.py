#
# References table definition
#

#from sqlobject import * 
#from bauble.plugins import BaubleTable
from bauble.treevieweditor import TreeViewEditorDialog


# TODO: references should be a many-to-many relationship with
# speciess since each species can have multiple references
# and each reference can refer to multiple speciess

# TODO: should have references in families, genera, speciess but
# if this is a multiple join i guess i would need to specify MultipleJoin
# columns for each

# TODO: should there be a reference type so we know if the references
# implies a book then we could look up extra information on amazon or
# something, probably better to just leave it as it is and if it is 
# URI then look it up, if not, then do nothing

#class Reference(BaubleTable):
#
#    # should only need either loc_id or site as long as whichever one is 
#    # unique, probably site, there is already and internal id
#    # what about subReferences, like if the References were the grounds
#    # and the sublocation is the block number
#    title = StringCol(length=64)
#    uri = StringCol()
#    
#    # the cascade=True means that if on of the records the foreignkey refers
#    # to is deleted then this reference is deleted as well, 
#    # is this what we want?
#    #species = ForeignKey("Species", default=None, cascade=True)
#    #family = ForeignKey("Family", default=None, cascade=True)
#    #genus = ForeignKey("Genus", default=None, cascade=True)
#
#    def __str__(self): 
#        return self.title
#    
#
#class ReferenceEditor(TreeViewEditorDialog):
#
#    visible_columns_pref = "editor.reference.columns"
#    column_width_pref = "editor.reference.column_width"
#    #default_visible_list = ['site', 'description'] 
#
#    label = 'References'
#
#    def __init__(self, parent=None, select=None, defaults={}):
#        TreeViewEditorDialog.__init__(self, Reference, "Reference Editor", 
#                                      parent, select=select, defaults=defaults)        
#        titles = {"label": "Label",
#                  "reference": "Reference",
#                  "speciesID": "Species",
#                  "familyID": "Family",
#                  "genusID": "Genus"}
#        self.columns.titles = titles
