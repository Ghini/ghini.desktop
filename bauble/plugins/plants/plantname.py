#
# Plantnames table definition
#

import gtk
from sqlobject import *
import bauble.utils as utils
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TreeViewEditorDialog, ComboColumn
from bauble.utils.log import log, debug


#
# Plantname table
#
class Plantname(BaubleTable):
    
    def __init__(self, **kw):
        super(Plantname, self).__init__(**kw)
        
#        self.values = {"sp_hybrid": [("H", "Hybrid formula"),
#                                     ("x", "Nothotaxon hybrid"),
#                                     ("+", "Graft hybrid/chimaera")],
#                       "sp_qual": [("agg.", "Aggregate"),
#                                   ("s. lat.", "sensu lato"),
#                                   ("s. str.", "sensu stricto")],     
#                      }
        
    #sp_hybrid = StringCol(length=1, default=None)  # species hybrid, x, H,...
    # species hybrid, x, H,...
    sp_hybrid = EnumCol(enumValues=("H", 
                                    "x", 
                                    "+",
                                    None), 
                        default=None) 
    
    
    sp_qual = EnumCol(enumValues=("agg.", 
                                  "s.lat.", 
                                  "s. str.",
                                  None), 
                      default=None)
    #sp_qual = StringCol(length=10, default=None)  # species qualifier, agg., s. lat, s.str
    #values["sp_qual"] = [("agg.", "Aggregate"),
    #                     ("s. lat.", "sensu lato"),
    #                     ("s. str.", "sensu stricto")]
                                                    
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
    #subgen_rank = StringCol(length=12, default=None)
    subgen_rank = EnumCol(enumValues=("subgenus", 
                                      "section", 
                                      "subsection",
                                      "series", 
                                      "subseries",
                                      None),
                          default=None)
#    values["subgen_rank"] = [("subgenus", "Subgenus"),
#                             ("section", "Section"),
#                             ("subsection", "Subsection"),
#                             ("series", "Series"),
#                             ("subseries", "Subseries")]
                             

    isp = StringCol(length=30, default=None)         # intraspecific epithet
    #isp_author = StringCol(length=254, default=None) # intraspecific author
    isp_author = UnicodeCol(length=255, dbEncoding="latin-1", default=None) # intraspecific author
    #isp_rank = StringCol(length=10, default=None)    # intraspecific rank
    isp_rank = EnumCol(enumValues=("subsp.", 
                                   "var.", 
                                   "subvar.", 
                                   "f.", 
                                   "subf.",
                                   None), 
                       default=None)
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
    
    # TODO: create distribution table that holds one of each of the 
    # geography tables which will hold the plants distribution, this
    # distribution table could even be part of the geography module

    # UPDATE: it might be better to do something like the source_type in the 
    # the accessions, do we need the distribution table if we're only
    # going to be holding one of the value from continent/region/etc, the only
    # exception is that we also need to hold a cultivated value and possible
    # something like "tropical", we can probably still use the distribution table
    # as long as setting to and from the distribution is handled silently
    #distribution = SingleJoin('Distribution', joinColumn='plantname_id', 
    #                           makeDefault=None)
    # right now we'll just include the string from one of the tdwg 
    # plant distribution tables though in the future it would be good
    # to have a SingleJoin to a distribution table so we get the extra
    # benefit of things like iso codes and hierarchial data, e.g. get
    # all plants from africa
    distribution = UnicodeCol(default=None)

    
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

        
#class DistributionColumn(ComboColumn):
#    
#    def __init__
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
        titles = {"genusID": "Genus",
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
#                   'iucn23': 'IUCN 2.3\nCategory',
#                   'iucn31': 'IUCN 3.1\nCategory',
                   'id_qual': 'ID qualifier',
                   'vernac_name': 'Common Name',
                   'poison_humans': 'Poisonious\nto humans',
                   'poison_animals': 'Poisonious\nto animals',
                   'food_plant': 'Food plant',
                   'distribution': 'Distribution'
                   }
        
        # make a custom distribution column
        self.columns.pop('distribution') # this probably isn't necessary     
        dist_column = ComboColumn(self.view, 'Distribution',
                           so_col = Plantname.sqlmeta.columns['distribution'])
        dist_column.model = self.make_model()
        self.columns['distribution'] = dist_column            
        
        self.columns.titles = titles
                     
        # set completions
        self.columns["genusID"].meta.get_completions = self.get_genus_completions
        
        
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
        #name = model.get_value(iter, 0)
        #id = model.get_value(iter, 1)
        genus = model.get_value(iter, 1)
                
        #model = self.view.get_model()
        #self.set_view_model_value(path, colname, [id, name])
        self.set_view_model_value(path, "genusID", genus)        
        
        
    def dist_cell_data_func(self, layout, cell, model, iter, data=None):
        v = model.get_value(iter, 0)
        if v is not None:
            dist = v['distribution']
            cell.set_property('text', str(dist))
        #cell.set_property('text', str(v))
        
    
    def on_dist_cell_key_press(self, widget, event, path, data=None):
        log.debug('on_dist_cell_key_press')
        keyname = gtk.gdk.keyval_name(event.keyval)
        log.debug("print keyname")
        path, col = self.view.get_cursor()
        if keyname == "Down":
            widget.popup()
        elif keyname in ["Left","Right"]:
            log.debug("move cursor " + keyname)
            self.move_cursor_next(path, col, keyname)

    
    def on_dist_editing_started(self, cell, combo, path, data=None):
        log.debug('on_dist_editing_started')
        #print combo.popup()
        #combo.connect("key-press-event", self.on_dist_cell_key_press, path)
        #combo.connect("changed", self.on_dist_combo_changed)
        
    
    combo_value = None
    def on_dist_combo_changed(self, combo, data=None):
        debug('dist_combo_changed')
        i = combo.get_active_iter()
        self.combo_value = combo.get_model().get_value(i, 1)
        
    def on_dist_renderer_edited(self, renderer, path, new_text, colname):
        debug('on_dist_renderer_edited')
        debug(new_text)
        model = self.view.get_model()        
        i = model.get_iter(path)        
        v = model.get_value(i, 0)        
        debug('v1: ' + str(v[colname]))
        #debug(model_val)
        #model_row = model_val[colname]
        #debug(model_row)        
        #model_row = self.combo_value
        #debug(model_row)
        #value = self.column_meta[colname].validate(new_text)
        self.set_view_model_value(path, colname, new_text)
        debug('v2: ' + str(v[colname]))
        
    def make_model2(self):
        model = gtk.TreeStore(object)
        model.append(None, ["Cultivated"])
        for continent in tables['Continent'].select(orderBy='continent'):
            p1 = model.append(None, [continent])
            for region in continent.regions:
                p2 = model.append(p1, [region])
                for country in region.botanical_countries:
                    p3 = model.append(p2, [country])
                    for unit in country.units:
                        if str(unit) != str(country):
                            model.append(p3, [unit])    
                            
    def make_model(self):
        model = gtk.TreeStore(str)
        model.append(None, ["Cultivated"])
        for continent in tables['Continent'].select(orderBy='continent'):
            p1 = model.append(None, [str(continent)])
            for region in continent.regions:
                p2 = model.append(p1, [str(region)])
                for country in region.botanical_countries:
                    p3 = model.append(p2, [str(country)])
                    for unit in country.units:
                        if str(unit) != str(country):
                            model.append(p3, [str(unit)])    
        return model
                            
    def create_dist_column(self):
        name = "distribution"
        renderer = gtk.CellRendererCombo()
        
        renderer.connect("editing_started", self.on_editing_started, name)
        model = gtk.ListStore(str)
        for d in "1234": 
            model.append([d])
        renderer.set_property("model",model)
        renderer.set_property('text-column', 0)
        renderer.set_property('editable', True)
        renderer.set_property('has_entry', False)
        renderer.connect("edited", self.on_dist_renderer_edited, name)
        #renderer.connect("editing_started", self.on_dist_editing_started, name)        
        #model = gtk.ListStore(str, object)
        model = self.make_model()            
        renderer.set_property("model", model)
        column = gtk.TreeViewColumn(self.column_meta['distribution'].header, renderer)
        column.set_cell_data_func(renderer, self.combo_cell_data_func, name)
        column.name = name
        return column
        
        
    def create_dist_column2(self):
        # create the renderer
        name = "distribution"
        renderer = gtk.CellRendererCombo()
        renderer.set_property('has_entry', True)
        renderer.set_property("editable", True)
        model = gtk.TreeStore(str)
        for d in "1234": 
            model.append(None, [d])
        renderer.set_property("model", model)
        
        renderer.connect("editing_started", self.on_editing_started, name)
        renderer.connect("edited", self.on_renderer_edited, name)
        
        # create the column
        column = gtk.TreeViewColumn(self.column_meta['distribution'].header, renderer)
        column.name = name # .name is my own data, not part of gtk
        column.set_min_width(50)
        column.set_clickable(True)
        column.set_resizable(True)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_reorderable(True)            
        column.set_cell_data_func(renderer, self.dist_cell_data_func, name)
                
        # TODO: we could probably do this in editor.py, have a method that adds
        # standard properties to column whether they are used created or not
        # notify when the column width property is changed        
        column.connect("notify::width", self.on_column_property_notify, name)
        column.connect("notify::visible", self.on_column_property_notify, name)        
        return column
        
        
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
    class PlantnameInfoBox(InfoBox):
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
            #self.ref = ReferenceExpander()
            #self.ref.set_expanded(True)
            #self.add_expander(self.ref)
            
            #img = ImagesExpander()
            #img.set_expanded(True)
            #self.add_expander(img)
            
            
        def update(self, row):
            pass
            #self.ref.update(row.references)
            #self.ref.value = row.references
            #ref = self.get_expander("References")
            #ref.set_values(row.references)
