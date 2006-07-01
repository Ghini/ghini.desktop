#
# Family table definition
#

import os, traceback
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
    return e.start() != None


def add_genera_callback(row):
    from bauble.plugins.plants.genus import GenusEditor    
    value = row[0]
    e = GenusEditor(defaults={'familyID': value})
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
# infobox
#
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander    
except ImportError:
    pass
else:    
    from sqlobject.sqlbuilder import *
    import bauble.paths as paths
    from bauble.plugins.plants.genus import Genus
    from bauble.plugins.plants.species_model import Species
    from bauble.plugins.garden.accession import Accession
    from bauble.plugins.garden.plant import Plant
    
    class GeneralFamilyExpander(InfoExpander):
        '''
        generic information about an family like number of genus, species,
        accessions and plants
        '''
    
        def __init__(self, glade_xml):
            '''
            the constructor
            '''
            InfoExpander.__init__(self, "General", glade_xml)
            general_box = self.widgets.fam_general_box
            if general_box.get_parent() is not None:
                general_box.get_parent().remove(general_box)
                
            self.vbox.pack_start(general_box)
            
            
        def update(self, row):
            '''
            update the expander
            
            @param row: the row to get the values from
            '''
            
            # TODO: need to figure out how to get the number of unique value
            # from a particular column in a table, see get_num_unique below
            
            self.set_widget_value('fam_name_data', str(row))
            
            ngen = Genus.select(Genus.q.familyID==row.id).count()
            self.set_widget_value('fam_ngen_data', ngen)
            
            conn = sqlhub.processConnection
            query_all = conn.queryAll
            sqlrepr = conn.sqlrepr
            def get_num_unique(query):
                unique = []
                num_unique = 0
                #for result in conn.queryAll(conn.sqlrepr(query)):
                for result in query_all(sqlrepr(query)):
                    if result[0] not in unique:
                        num_unique += 1
                        unique.append(result[0])
                return num_unique
                                                        
            # get the number of species
            species_query = AND(Species.q.genusID == Genus.q.id, 
                                Genus.q.familyID==row.id)            
            nsp = Species.select(species_query).count()                        
            query = Select(Species.q.genusID, where=species_query)            
            ngen_with_species = get_num_unique(query)
                                 
            # get the number of accessions
            acc_query = AND(Accession.q.speciesID == Species.q.id,
                            Species.q.genusID == Genus.q.id, 
                            Genus.q.familyID==row.id)
            nacc = Accession.select(acc_query).count()
            unique = []
            query = Select(Accession.q.speciesID, where=acc_query)
            nsp_with_accessions = get_num_unique(query)
                        
            # get the number of plants
            plants_query = AND(Plant.q.accessionID == Accession.q.id,
                               Accession.q.speciesID == Species.q.id,
                               Species.q.genusID == Genus.q.id, 
                               Genus.q.familyID==row.id)            
            nplants = Plant.select(plants_query).count()
            query = Select(Plant.q.accessionID, where=plants_query)
            nacc_with_plants = get_num_unique(query)

            # select count(s) 
            # from species s, 
            #      genus g, 
            #      family f 
            # where f.family='Sapindaceae' 
            #   and g.family_id = f.id 
            #   and s.genus_id = g.id;
            
            #debug(conn.sqlrepr(sql))
            # select counts(s)
            # from species s,
            #      (select g.genus, g.id
            #       from genus g, 
            #            (select family, id
            #             from family f 
            #             where family='Sapindaceae') AS fam
            #       where g.family_id=fam.id) AS gen
            #where s.genus_id=gen.id;
            
            nsp_str = '0'
            if nsp > 0:
                nsp_str = '%s in %s genera' % (nsp, ngen_with_species)
            self.set_widget_value('fam_nsp_data', nsp_str)
            
            nacc_str = '0'    
            if nacc > 0:
                nacc_str = '%s in %s species' % (nacc, nsp_with_accessions)
            self.set_widget_value('fam_nacc_data', nacc_str)
            
            nplants_str = '0'
            if nplants > 0:
                nplants_str = '%s in %s accessions' % (nplants, nacc_with_plants)            
            self.set_widget_value('fam_nplants_data', nplants_str)
                
                
    class FamilyInfoBox(InfoBox):
        '''
        '''
        
        def __init__(self):
            '''
            '''
            InfoBox.__init__(self)
            glade_file = os.path.join(paths.lib_dir(), 'plugins', 'plants', 
                                      'infoboxes.glade')            
            self.glade_xml = gtk.glade.XML(glade_file)            
            self.general = GeneralFamilyExpander(self.glade_xml)
            self.add_expander(self.general)
        
        def update(self, row):
            '''
            '''
            self.general.update(row)