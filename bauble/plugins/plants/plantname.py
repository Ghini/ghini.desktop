#
# Plantnames table definition
#

import utils
#from tables import *
from sqlobject import *

from bauble.plugins import BaubleTable, tables
from bauble.plugins.editor import TreeViewEditorDialog

#
# Plantname table
#
class Plantname(BaubleTable):
    
    def __init__(self, **kw):
        super(Plantname, self).__init__(**kw)
        
        self.values = {"sp_hybrid": [("H", "Hybrid formula"),
                                     ("x", "Nothotaxon hybrid"),
                                     ("+", "Graft hybrid/chimaera")],
                       "sp_qual": [("agg.", "Aggregate"),
                                   ("s. lat.", "sensu lato"),
                                   ("s. str.", "sensu stricto")],     
                      }
        
    sp_hybrid = StringCol(length=1, default=None)  # species hybrid, x, H,...
    
    sp_qual = StringCol(length=10, default=None)  # species qualifier, agg., s. lat, s.str
#    values["sp_qual"] = [("agg.", "Aggregate"),
#                         ("s. lat.", "sensu lato"),
#                         ("s. str.", "sensu stricto")]
                                                    
    sp = StringCol(length=40, notNull=True)          # specific epithet
    #sp_author = StringCol(length=255, default=None)  # species author
    #sp_author = UnicodeCol(dbEncoding='latin-1', default=None)  # species author
    sp_author = UnicodeCol(default=None)  # species author
        
    cv_group = StringCol(length=50, default=None)    # cultivar group
    cv = StringCol(length=30, default=None)          # cultivar epithet
    trades = StringCol(length=50, default=None)      # trades, e.g. "Sundance"

    # full name shouldn't be necessary
    #full_name = StringCol(length=50, default=None)
    
    supfam = StringCol(length=30, default=None)  
        
    subgen = StringCol(length=50, default=None)
    subgen_rank = StringCol(length=12, default=None)
#    values["subgen_rank"] = [("subgenus", "Subgenus"),
#                             ("section", "Section"),
#                             ("subsection", "Subsection"),
#                             ("series", "Series"),
#                             ("subseries", "Subseries")]
                             

    isp = StringCol(length=30, default=None)         # intraspecific epithet
    #isp_author = StringCol(length=254, default=None) # intraspecific author
    isp_author = UnicodeCol(length=255, dbEncoding="latin-1", default=None) # intraspecific author
    isp_rank = StringCol(length=10, default=None)    # intraspecific rank
#    values["isp_rank"] = [("subsp.", "Subspecies"),
#                          ("var.", "Variety"),
#                          ("subvar.", "Subvariety"),
#                          ("f.", "Forma"),
#                          ("subf.", "Subform")]

    isp2 = StringCol(length=30, default=None)
    isp2_author = UnicodeCol(length=254, default=None)
    isp2_rank = StringCol(length=10, default=None)
#    values["isp2_rank"] = [("subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]


    isp3 = StringCol(length=30, default=None)
    isp3_author = UnicodeCol(length=254, default=None)
    isp3_rank = StringCol(length=10, default=None)
#    values["isp3_rank"] = [( "subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]

    isp4 = StringCol(length=30, default=None)
    isp4_author = UnicodeCol(length=254, default=None)
    isp4_rank = StringCol(length=10, default=None)
#    values["isp4_rank"] = [( "subsp.", "Subspecies"),
#                           ("var.", "Variety"),
#                           ("subvar.", "Subvariety"),
#                           ("f.", "Forma"),
#                           ("subf.", "Subform")]

    # TODO: maybe the IUCN information should be looked up online
    # rather than being entered in the database or maybe there could
    # be an option to lookup the code online
    iucn23 = StringCol(length=5, default=None)  # iucn category version 2.3
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
    
    iucn31 = StringCol(length=50, default=None) # iucn category_version 3.1
#    values["iucn31"] = [("EX", "Extinct"),
#                        ("EW", "Extinct in the wild"),
#                        ("CR", "Critically endangered"),
#                        ("EN", "Endangered"),
#                        ("VU", "Vulnerable"),
#                        ("NT", "Near threatened"), 
#                        ("LC", "Least consern"), 
#                        ("DD", "Data deficient"),
#                        ("NE", "Not evaluated")]
    
    #rank_qual = StringCol(length=1, default=None) # rank qualifier, a single character
    
    id_qual = StringCol(length=10, default=None)#id qualifier, aff., cf., etc...
#    values["id_qual"] = [("aff.", "Akin to or bordering"),
#                         ("cf.", "compare with"),
#                         ("Incorrect", "Incorrect"),
#                         ("forsan", "Perhaps"),
#                         ("near", "Close to"),
#                         ("?", "Quesionable")]
    
    # TODO: should be unicode
    vernac_name = StringCol(default=None)          # vernacular name

#    synonym = StringCol(default=None)  # should really be an id into table \
#                                       # or there should be a syn table
    
    # where this name stands in taxonomy, whether it's a synonym or
    # not basically, would probably be better to just leaves this and
    # look it up on www.ipni.org www.itis.usda.gov
    #taxonomic_status = StringCol()
    synonyms = MultipleJoin('Synonyms', joinColumn='plantname_id')
    
    poison_humans = BoolCol(default=None)
    poison_animals = BoolCol(default=None)
    food_plant = StringCol(length=50, default=None)

    # origin, should be value from one of the country
    # tables, i think the values of the country tables can be combined
    # into a string to give more specific information, either that or
    # maybe an index into one of the tables with the value being chosen
    # from a combo
    origin = StringCol(default=None)
    # TODO: create distribution table that holds one of each of the 
    # geography tables which will hold the plants distribution, this
    # distribution table could even be part of the geography module
    #distribution = SingleJoin('Distribution')


    
    # foreign keys and joins
    genus = ForeignKey('Genus', notNull=True)
    #accessions = MultipleJoin('Accessions', joinColumn='plantname_id')
    #images = MultipleJoin('Images', joinColumn='plantname_id')
    #references = MultipleJoin('Reference', joinColumn='plantname_id')
    
    
    ######## the rest? ##############    
    #Lifeform = StringCol(length=10)
#    tuses = StringCol(default=None) # taxon uses?
#    trange = StringCol(default=None)# taxon range?
    #pcomments = StringCol()
    #Source1 = IntCol()
    #Source2 = IntCol()
    #Initials1st = StringCol(length=50)
    #InitialsC = StringCol(length=50)

        
    # internal
    #Entered = DateTimeCol()
    #Updated = DateTimeCol()
    #Changed = DateTimeCol()

    def __str__(self):
        return utils.plantname2str(self)
        
#
# Plantname editor
#
class PlantnameEditor(TreeViewEditorDialog):
    
    visible_columns_pref = "editor.plantname.columns"
    column_width_pref = "editor.plantname.column_width"
    default_visible_list = ['genus', 'sp']
    
    label = 'Plant Names'
    
    def __init__(self, parent=None, select=None, defaults={}):  
        TreeViewEditorDialog.__init__(self, tables["Plantname"],
                                      "Plantname Editor", parent,
                                      select=select, defaults=defaults)
        headers = {"genus": "Genus",
                   "sp": "Species",
                   "sp_hybrid": "Sp. hybrid",
                   "sp_qual": "Sp. qualifier",
                   "sp_author": "Sp. author",
                   "cv_group": "Cv. group",
                   "cv": "Cultivar",
                   "trades": "Trade name",
                   "supfam": 'Super family',
                   'subgen': 'Subgenus',
                   'subgen_rank': 'Subgeneric rank',
                   'isp': 'Intraspecific\nepithet',
                   'isp_rank': 'Isp. rank',
                   'isp_author': 'Isp. author',
                   'isp2': 'Isp. 2',
                   'isp2_rank': 'Isp. 2 rank',
                   'isp2_author': 'Isp. 2 author',
                   'isp3': 'Isp. 3',
                   'isp3_rank': 'Isp. 3 rank',
                   'isp3_author': 'Isp. 3 author',
                   'isp4': 'Isp. 4',
                   'isp4_rank': 'Isp. 4 rank',
                   'isp4_author': 'Isp. 4 author',
                   'iucn23': 'IUCN 2.3\nCategory',
                   'iucn31': 'IUCN 3.1\nCategory',
                   'id_qual': 'ID qualifier',
                   'vernac_name': 'Common Name',
                   'poison_humans': 'Poisonious\nto humans',
                   'poison_animals': 'Poisonious\nto animals',
                   'food_plant': 'Food plant'
                   }
        self.column_meta.headers = headers        

        
    def foreign_does_not_exist(self, name, value):
        self.add_genus(value)    


    def add_genus(self, name):
        msg = "The Genus %s does not exist. Would you like to add it?" % name
        if utils.yes_no_dialog(msg):

            print "add genus"

    def get_completions(self, text, colname):
        maxlen = -1
        model = None
        if colname == "genus":
            model = gtk.ListStore(str, int)
            if len(text) > 2:
                sr = tables["Genus"].select("genus LIKE '"+text+"%'")
                for row in sr: model.append([str(row), row.id])
        return model, maxlen
        
        
#
# Plantname infobox for SearchView
#
try:
    from bauble.plugins.searchview.infobox import InfoBox, InfoExpander
except ImportError:
    pass
else:
    class PlantnamesInfoBox(InfoBox):
        """
        - general info, fullname, common name, num of accessions and clones
        - reference
        - images
        - redlist status
        - poisonous to humans
        - poisonous to animals
        - food plant
        - origin
        """
        def __init__(self):
            """ 
            fullname, synonyms, ...
            """
            InfoBox.__init__(self)
            self.ref = ReferencesExpander()
            self.ref.set_expanded(True)
            self.add_expander(self.ref)
            
            #img = ImagesExpander()
            #img.set_expanded(True)
            #self.add_expander(img)
            
            
        def update(self, row):
            self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
