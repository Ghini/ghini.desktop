#
# Species table definition
#
import os
import gtk
from sqlobject import *
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog, ComboColumn, TextColumn
from bauble.utils.log import log, debug
#from speciesmeta import SpeciesMeta
    
#
# Species table
#
class Species(BaubleTable):
    
    def __init__(self, **kw):
        super(Species, self).__init__(**kw)
        
    sp_hybrid = EnumCol(enumValues=("H", 
                                    "x", 
                                    "+",
                                    ""), 
                        default="") 
    
    
    sp_qual = EnumCol(enumValues=("agg.", 
                                  "s.lat.", 
                                  "s. str.",
                                  ""), 
                      default="")
                                                    
    sp = StringCol(length=40, notNull=True)          # specific epithet
    sp_author = UnicodeCol(default=None)  # species author
        
    cv_group = StringCol(length=50, default=None)    # cultivar group
    #cv = StringCol(length=30, default=None)          # cultivar epithet
    #trades = StringCol(length=50, default=None)      # trades, e.g. "Sundance"
    
#    supfam = StringCol(length=30, default=None)          
#    subgen = StringCol(length=50, default=None)
#    subgen_rank = EnumCol(enumValues=("subgenus", 
#                                      "section", 
#                                      "subsection",
#                                      "series", 
#                                      "subseries",
#                                      None),
#                          default=None)                             

    isp = StringCol(length=30, default=None)         # intraspecific epithet
    isp_author = UnicodeCol(length=255, default=None) # intraspecific author
    # intraspecific rank
    isp_rank = EnumCol(enumValues=("subsp.", # subspecies
                                   "var.",   # variety
                                   "subvar.", # sub variety
                                   "f.",     # form
                                   "subf.",  # subform
                                   "cv.",    # cultivar                                   
                                   ""), 
                       default="")

#    isp2 = StringCol(length=30, default=None)
#    isp2_author = UnicodeCol(length=254, default=None)
#    isp2_rank = StringCol(length=10, default=None)
#
#
#    isp3 = StringCol(length=30, default=None)
#    isp3_author = UnicodeCol(length=254, default=None)
#    isp3_rank = StringCol(length=10, default=None)
#
#
#    isp4 = StringCol(length=30, default=None)
#    isp4_author = UnicodeCol(length=254, default=None)
#    isp4_rank = StringCol(length=10, default=None)
    

    # TODO: maybe the IUCN information should be looked up online
    # rather than being entered in the database or maybe there could
    # be an option to lookup the code online
    #iucn23 = StringCol(length=5, default=None)  # iucn category version 2.3
#    values["iucn23"] = [("EX", "Extinct"),
#                        ("EW", "Extinct in the wild"),
#                        ("CR", "Critically endangered"),
#                        ("EN", "Endangered"),
#                        ("VU", "Vulnerable"),
#                        #("LR", "Low risk"),
#                        ("CD", "Conservation dependent"), # low risk cat 1
#                        ("NT", "Near threatened"), # low risk cat 2
#                        ("LC", "Least consern"), # low risk cat 3
#                        ("DD", "Data deficient"),
#                        ("NE", "Not evaluated")]
    
    #iucn31 = StringCol(length=50, default=None) # iucn category_version 3.1
#    values["iucn31"] = [("EX", "Extinct"),
#                        ("EW", "Extinct in the wild"),
#                        ("CR", "Critically endangered"),
#                        ("EN", "Endangered"),
#                        ("VU", "Vulnerable"),
#                        ("NT", "Near threatened"), 
#                        ("LC", "Least consern"), 
#                        ("DD", "Data deficient"),
#                        ("NE", "Not evaluated")]
    
    #rank_qual = StringCol(length=1, default=None) # rank qualifier, a single
    # character
    
    id_qual = EnumCol(enumValues=("aff.", # Akin to or bordering
                                  "cf.", # compare with
                                  "Incorrect", # Incorrect
                                  "forsan", # Perhaps
                                  "near", # Close to
                                  "?", # Quesionable
                                  ""),
                      default="")
    
    # TODO: should be unicode
    vernacular_name = UnicodeCol(default=None) # vernacular name
    # it would be best to display the vernacular names in a dropdown list
    # with a way to add to the list    
    #vernacular_names = MultipleJoin('VernacularName', joinColumn='species_id')
    # this is the default vernacular name we'll use
    #default_vernacular_name = ForeignKey('VernacularName')
    #default_vernacular_name = SingleJoin('VernacularName', 
    #                                     joinColumn='species_id')
    
#    synonym = StringCol(default=None)  # should really be an id into table \
#                                       # or there should be a syn table
    
    # where this name stands in taxonomy, whether it's a synonym or
    # not basically, would probably be better to just leaves this and
    # look it up on www.ipni.org www.itis.usda.gov
    #taxonomic_status = StringCol()
    synonyms = MultipleJoin('Synonyms', joinColumn='species_id')
        
    # foreign keys and joins
    genus = ForeignKey('Genus', notNull=True)
    #accessions = MultipleJoin('Accessions', joinColumn='species_id')
    #images = MultipleJoin('Images', joinColumn='species_id')
    #references = MultipleJoin('Reference', joinColumn='species_id')
    
    notes = UnicodeCol(default=None)
    
    # hold meta information about this plant
    species_meta = SingleJoin('SpeciesMeta', joinColumn='species_id')        

    
    def __str__(self):
          #TODO: this needs alot of work to be complete
        #name = str(self.genus) + " " + self.sp
        #if self.isp_rank is not None:
        #    name = "%s %s %s" % (name, self.isp_rank, self.isp)
        #return name.strip()
        return Species.str(self)
    
    
    def markup(self, authors=False):
        return Species.str(self, authors, True)
    
    
    @staticmethod
    def str(species, authors=False, markup=False):
        """
        return the full plant name string
        NOTE: it may be better to create a separate method for the markup
        since substituting into the italic make slow things down, should do 
        some benchmarks. also, which is faster, doing substitution this way or
        by using concatenation
        """    
        # TODO: should do a translation table for any entities that might
        # be in the author strings ans use translate, what else besided 
        # ampersand could be in the author name
        if markup:
            italic = "<i>%s</i>"
        else:
            italic = "%s"
        #name = "%s %s" % (italic % str(species.genus), italic % species.sp)
        name = italic % str(species.genus)
        
        # take care of species hybrid
        if not species.sp_hybrid == "":
            # we don't have a second sp name for the hyrbid formula right now
            # so we'll just use the isp for now
            if species.isp is not None:
                name += " %s %s %s " % (italic % species.sp, 
                                        species.sp_hybrid,
                                        italic % species.isp)
            else:
                name += ' %s %s' % (species.sp_hybrid, species.sp)
        else:
            name += ' ' + italic % species.sp
            
        # cultivar groups and cultivars
        if species.cv_group is not None:
            if species.isp_rank == "cv.":
                name += ' (' + species.cv_group + " Group) '" + \
                italic % species.isp + "'"
            else: 
                name += ' ' + species.cv_group + ' Group'
            return name
        
        if species.sp_author is not None and authors is not False:
            name += ' ' + species.sp_author.replace('&', '&amp;')
        if not species.isp_rank == "":
            if species.isp_rank == "cv.":
                name += " '" + species.isp + "'"
            else:
                name += ' ' + species.isp_rank + ' ' + \
                              italic % species.isp
                if species.isp_author is not None and authors is not False:
                    name += ' ' + species.isp_author
        return name
    
    
        
#class DistributionColumn(ComboColumn):
#    
#    def __init__
#
# Species editor
#
class SpeciesEditor(TreeViewEditorDialog):
    
    visible_columns_pref = "editor.species.columns"
    column_width_pref = "editor.species.column_width"
    default_visible_list = ['genus', 'sp']
    
    label = 'Species'
    
    def __init__(self, parent=None, select=None, defaults={}):  
        TreeViewEditorDialog.__init__(self, tables["Species"],
                                      "Species Editor", parent,
                                      select=select, defaults=defaults)
        titles = {"genusID": "Genus",
                   "sp": "Species",
                   "sp_hybrid": "Sp. hybrid",
                   "sp_qual": "Sp. qualifier",
                   "sp_author": "Sp. author",
                   "cv_group": "Cv. group",
#                   "cv": "Cultivar",
#                   "trades": "Trade name",
#                   "supfam": 'Super family',
#                   'subgen': 'Subgenus',
#                   'subgen_rank': 'Subgeneric rank',
                   'isp': 'Isp. epithet',
                   'isp_rank': 'Isp. rank',
                   'isp_author': 'Isp. author',
#                    'isp2': 'Isp. 2',
#                    'isp2_rank': 'Isp. 2 rank',
#                    'isp2_author': 'Isp. 2 author',
#                    'isp3': 'Isp. 3',
#                    'isp3_rank': 'Isp. 3 rank',
#                    'isp3_author': 'Isp. 3 author',
#                    'isp4': 'Isp. 4',
#                    'isp4_rank': 'Isp. 4 rank',
#                    'isp4_author': 'Isp. 4 author',
#                   'iucn23': 'IUCN 2.3\nCategory',
#                   'iucn31': 'IUCN 3.1\nCategory',
                   'id_qual': 'ID qualifier',
#                   'vernac_name': 'Common Name',
#                   'poison_humans': 'Poisonious\nto humans',
#                  'poison_animals': 'Poisonious\nto animals',
#                   'food_plant': 'Food plant',
#                   'distribution': 'Distribution'
                    'species_meta': 'Meta Info',
                    'notes': 'Notes',
                    'vernacular_name': 'Vernacular Name'
#                    'default_vernacular_name': 'Vernacular Names'
                   }
        
        # make a custom distribution column
#        self.columns.pop('distribution') # this probably isn't necessary     
#        dist_column = ComboColumn(self.view, 'Distribution',
#                           so_col = Species.sqlmeta.columns['distribution'])
#        dist_column.model = self.make_model()
#        self.columns['distribution'] = dist_column                    
        #self.columns['species_meta'] = \
        #    TextColumn(self.view, 'Species Meta', so_col=Species.sqlmeta.joins['species_meta'])
        #self.columns['default_vernacular_name'].meta.editor = \
        #    editors['VernacularNameEditor']
        self.columns['species_meta'].meta.editor = editors["SpeciesMetaEditor"]
        self.columns.titles = titles            
                     
        # set completions
        self.columns["genusID"].meta.get_completions= self.get_genus_completions
        
    
    class dict_obj(object):
        
        def __init__(self, d):
            self.dic = d
        def __getattr__(self, item):
            return self.dic[item]
    
        
    def commit_changes_NO(self):
        # TODO: speciess are a complex typle where more than one field
        # make the plant unique, write a custom commit_changes to get the value
        # from the table as a dictionary, convert this dictionary to 
        # an object that can be accessed by attributes so it mimic a 
        # Species object, pass the dict to species2str and test
        # that a species with the same name doesn't already exist in the 
        # database, if it does exist then ask the use what they want to do
        #super(SpeciesEditor, self).commit_changes()
        values = self.get_values_from_view()
    
    # from http://vsbabu.org/mt/archives/2003/02/13/joy_of_python_classes_and_dictionaries.html
    def dict2class(d):
        """Return a class that has same attributes/values and
           dictionaries key/value
        """
        
        #see if it is indeed a dictionary
        if type(d) != types.DictType:
            return None
        
        #define a dummy class
        class Dummy:
            pass
            
        c = Dummy
        for elem in d.keys():
            c.__dict__[elem] = d[elem]
        return c
        
    def test_values_before_commit(self, values):    
        #s = utils.species2str(dict2class(values)): 
        #if s == 
        # need to test each of the values that make up the species
        # against the database, not just the string, i guess we need to
        # check each of the keys in values, check if they are name components
        # use each of these values in a query to speciess
        if values.has_key('id'):
            return True
        exists = False
        select_values = {}
        debug(values)
        select_values['genusID'] = values['genusID'].id
        select_values['sp'] = values['sp']        
        sel = Species.selectBy(**select_values)
        names = ""
        for s in sel:
            exists = True
            names += "%d: %s\n" % (s.id, s)
        msg  = "The following plant names are similiar to the plant name you "\
               "are trying to create. Are your sure this is what you want to "\
               "do?\n\n" + names
        if exists and not utils.yes_no_dialog(msg):
            return False
        return True
            

    # 
    def get_genus_completions(self, text):
        model = gtk.ListStore(str, object)
        sr = tables["Genus"].select("genus LIKE '"+text+"%'")        
        for row in sr: 
            model.append([str(row), row])
        return model
                
    
    def on_genus_completion_match_selected(self, completion, model, 
                                           iter, path):
        """
        all foreign keys should use entry completion so you can't type in
        values that don't already exists in the database, therefore, allthough
        i don't like it the view.model.row is set here for foreign key columns
        and in self.on_renderer_edited for other column types                
        """        
        genus = model.get_value(iter, 1)
        self.set_view_model_value(path, "genusID", genus)        
        
                                    
#    def make_model(self):
#        model = gtk.TreeStore(str)
#        model.append(None, ["Cultivated"])
#        for continent in tables['Continent'].select(orderBy='continent'):
#            p1 = model.append(None, [str(continent)])
#            for region in continent.regions:
#                p2 = model.append(p1, [str(region)])
#                for country in region.botanical_countries:
#                    p3 = model.append(p2, [str(country)])
#                    for unit in country.units:
#                        if str(unit) != str(country):
#                            model.append(p3, [str(unit)])    
#        return model
                            
      
    def foreign_does_not_exist(self, name, value):
        self.add_genus(value)    


    def add_genus(self, name):
        msg = "The Genus %s does not exist. Would you like to add it?" % name
        if utils.yes_no_dialog(msg):
            print "add genus"

        
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander, \
        set_widget_value
except ImportError:
    pass
else:
    
#    
# Species infobox for SearchView
#
    class GeneralSpeciesExpander(InfoExpander):
        """
        generic information about an accession like
        number of clones, provenance type, wild provenance type, speciess
        """
    
        def __init__(self, glade_xml):
            InfoExpander.__init__(self, "General", glade_xml)
            w = self.glade_xml.get_widget('general_box')
            w.unparent()
            self.vbox.pack_start(w)
        
        
        def update(self, row):
            set_widget_value(self.glade_xml, 'name_data', 
                             Species.str(row, True, True))
            set_widget_value(self.glade_xml, 'nacc_data', len(row.accessions))
            
            nplants = 0
            for acc in row.accessions:
                nplants += len(acc.plants)
            set_widget_value(self.glade_xml, 'nplants_data', nplants)    
    
    
    class SpeciesInfoBox(InfoBox):
        """
        - general info, fullname, common name, num of accessions and clones
        - reference
        - images
        - redlist status
        - poisonous to humans
        - poisonous to animals
        - food plant
        - origin/distrobution
        """
        def __init__(self):
            """ 
            fullname, synonyms, ...
            """
            InfoBox.__init__(self)
            path = os.path.join(paths.lib_dir(), "plugins", "plants")
            self.glade_xml = gtk.glade.XML(path + os.sep + "species_infobox.glade")
            
            self.general = GeneralSpeciesExpander(self.glade_xml)
            self.add_expander(self.general)
            
            #self.ref = ReferenceExpander()
            #self.ref.set_expanded(True)
            #self.add_expander(self.ref)
            
            #img = ImagesExpander()
            #img.set_expanded(True)
            #self.add_expander(img)
            
            
        def update(self, row):
            self.general.update(row)
            #self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
        
