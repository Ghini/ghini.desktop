#
# Family table definition
#

import traceback
import gtk
from sqlobject import *
import bauble
from bauble.plugins import BaubleTable, tables, editors
from bauble.treevieweditor import TreeViewEditorDialog
from datetime import datetime
import bauble.utils as utils
from bauble.utils.log import debug


def edit_callback(row):
    value = row[0]    
    # TODO: the select paramater can go away when we move FamilyEditor to the 
    # new style editors    
    e = FamilyEditor(select=[value], model=value)
    e.start()


def add_genera_callback(row):
    from bauble.plugins.plants.genus import GenusEditor    
    value = row[0]
    e = GenusEditor(defaults={'familyID': value})
    e.start()


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
            #self.refresh_search()                
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


family_context_menu = [('Edit', edit_callback),
                       ('--', None),
                       ('Add genera', add_genera_callback),
                       ('--', None),
                       ('Remove', remove_callback)]

        
def family_markup_func(family):
    '''
    '''
    return str(family)



class Family(BaubleTable):

    class sqlmeta(BaubleTable.sqlmeta):
        defaultOrder = 'family'

    family = StringCol(length=45, notNull=True)#, alternateID="True")
    
    '''    
    The qualifier field designates the botanical status of the family.
    Possible values:
        s. lat. - aggregrate family (sensu lato)
        s. str. segregate family (sensu stricto)
    '''
    qualifier = EnumCol(enumValues=('s. lat.', 's. str.', None), default=None)
    notes = UnicodeCol(default=None)
    
    # indices
    family_index = DatabaseIndex('family', 'qualifier', unique=True)    
    
    # joins
    synonyms = MultipleJoin('FamilySynonym', joinColumn='family_id')    
    genera = MultipleJoin("Genus", joinColumn="family_id")
    
        
    def __str__(self): 
        # TODO: need ability to include the qualifier as part of the name, 
        # maybe as a keyworkd argument flag        
        return self.family
    
    @staticmethod
    def str(family, full_string=False):
        if full_string and family.qualifier is not None:
            return '%s (%s)' % (family.family, family.qualifier)
        else:
            return family.family
    
    
    
class FamilySynonym(BaubleTable):
    
    # - deleting either of the families that this synonym refers to makes this
    # synonym irrelevant
    # - here default=None b/c this can only be edited as a sub editor of,
    # Family, thoughwe have to be careful this doesn't create a dangling record
    # with no parent
    family = ForeignKey('Family', default=None, cascade=True)
    synonym = ForeignKey('Family', cascade=True)
    
    def __str__(self): 
        return self.synonym


# 
# editor
#
class FamilyEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.family.columns"
    column_width_pref = "editor.family.column_width"
    default_visible_list = ['family', 'comments']
    
    label = 'Families'
    
    def __init__(self, parent=None, select=None, defaults={}, **kwargs):
        
        TreeViewEditorDialog.__init__(self, tables["Family"], "Family Editor", 
                                      parent, select=select, defaults=defaults, 
                                      **kwargs)
        titles = {'family': 'Family',
                  'notes': 'Notes',
                  'qualifier': 'Qualifier',
                  'synonyms': 'Synonyms'}
        self.columns.titles = titles
        self.columns['synonyms'].meta.editor = editors["FamilySynonymEditor"]



# 
# FamilySynonymEditor
#
class FamilySynonymEditor(TreeViewEditorDialog):

    visible_columns_pref = "editor.family_syn.columns"
    column_width_pref = "editor.family_syn.column_width"
    default_visible_list = ['synonym']
    
    standalone = False
    label = 'Family Synonym'
    
    def __init__(self, parent=None, select=None, defaults={}, **kwargs):        
        TreeViewEditorDialog.__init__(self, tables["FamilySynonym"],
                                      "Family Synonym Editor", 
                                      parent, select=select, 
                                      defaults=defaults, **kwargs)
        titles = {'synonymID': 'Synonym of Family'}
                  
        # can't be edited as a standalone so the family should only be set by
        # the parent editor
        self.columns.pop('familyID')
        
        self.columns.titles = titles
        self.columns["synonymID"].meta.get_completions = self.get_family_completions

        
    def get_family_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Family"].select("family LIKE '"+text+"%'")
        for row in sr:
            model.append([str(row), row])
        return model


#
# infobox for SearchView
# 
try:
    from bauble.plugins.searchview.infobox import InfoBox
except ImportError:
    pass
else:
    class FamiliesInfoBox(InfoBox):
        """
        - number of taxon in number of genera
        - references
        """
        def __init__(self):
            InfoBox.__init__(self)
