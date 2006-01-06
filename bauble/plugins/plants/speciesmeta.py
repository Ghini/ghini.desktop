#
# Species table definition
#
import os, traceback
import gtk
from sqlobject import *
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TableEditorDialog, ComboColumn
from bauble.utils.log import log, debug

# TODO create a meta table that holds information about a species 
# like poisonous, etc. that way we don't have to bumble up species everytime
# we want to add more meta information
# TODO: allow us to search on somthing like meta=poisonous
class SpeciesMeta(BaubleTable):
    
    poison_humans = BoolCol(default=None)
    poison_animals = BoolCol(default=None)
    
    # poison_humans should imply food_plant false or whatever value
    # is meant to be in food_plant
    #food_plant = StringCol(length=50, default=None)
    food_plant = BoolCol(default=None)
    
    # TODO: create distribution table that holds one of each of the 
    # geography tables which will hold the plants distribution, this
    # distribution table could even be part of the geography module

    # UPDATE: it might be better to do something like the source_type in the 
    # the accessions, do we need the distribution table if we're only
    # going to be holding one of the value from continent/region/etc, the only
    # exception is that we also need to hold a cultivated value and possible
    # something like "tropical", we can probably still use the distribution
    # table as long as setting to and from the distribution is handled silently
    #distribution = SingleJoin('Distribution', joinColumn='species_id', 
    #                           makeDefault=None)
    # right now we'll just include the string from one of the tdwg 
    # plant distribution tables though in the future it would be good
    # to have a SingleJoin to a distribution table so we get the extra
    # benefit of things like iso codes and hierarchial data, e.g. get
    # all plants from africa
    distribution = UnicodeCol(default=None)
    
    # this should be set by the editor
    # FIXME: this could be dangerous and cause dangling meta information
    # - removing the species removes this meta info
    species = ForeignKey('Species', default=None, cascade=True)
    
    def __str__(self):
        v = []
        if self.distribution is not None:
            v.append(self.distribution)
        if self.food_plant is not None and self.food_plant:
            v.append('Food')
        if self.poison_humans is not None and self.poison_humans:
            v.append('Poisonous')
        if self.poison_animals is not None and self.poison_animals:
            v.append('Poisonous to animals')            
        return ','.join(v)
    
    
class SpeciesMetaEditor(TableEditorDialog):
    
    standalone = False
    label = 'Species Meta'
    
    def __init__(self, select=None, defaults={}):
        super(SpeciesMetaEditor, self).__init__(tables["SpeciesMeta"], 
                                                'Species Meta Test', None,
                                                select, defaults)
        path = os.path.join(paths.lib_dir(), 'plugins', 'plants')
        self.glade_xml = gtk.glade.XML(path + os.sep + 'speciesmeta.glade')
        
        # override dialog from TableEditorDialog
#        self.dialog.destroy() # TODO: is this safe???
        #self.dialog = self.glade_xml.get_widget('main_dialog')
	self.dialog.set_resizable(False)
	vbox = self.glade_xml.get_widget('main_box')
	vbox.unparent()
	self.dialog.vbox.pack_start(vbox)
	
        self.dist_combo = self.glade_xml.get_widget('dist_combo')
        self.committed = False
        self.food_check = self.glade_xml.get_widget('food_check')
        self.poison_animals_check = \
            self.glade_xml.get_widget('poison_animals_check')            
        self.poison_humans_check = \
            self.glade_xml.get_widget('poison_humans_check')
        self.__values = None
    
    
    def start(self, commit_transaction):
        self.__populate_distribution_combo()
        if self.select is not None:
            self._set_widget_values_from_instance(self.select)
        committed = self._run()
        if commit_transaction:
            sqlhub.processConnection.commit()
        return committed
    
        
    
    def commit_changes(self):
        '''
        we just implement this since species meta should only ever return
        a single value
        '''
        # if we were passed in an object to edit make sure we keep the same
        # id so we don't wind up with multple SpeciesMeta for one Species
        if self.select is not None:
            self.__values['id'] = self.select.id
        table_instance = self._commit(self.__values)
        return table_instance


    def _set_widget_values_from_instance(self, meta):
        '''
        set the widgets in the editor from the meta instance
        '''
        
        # set the distribution
        def find_dist(model, path, iter, dist):
            if model[iter][0] == dist:
                self.dist_combo.set_active_iter(iter)
                return True        
        model = self.dist_combo.get_model()
        model.foreach(find_dist, meta.distribution)
        
        if meta.food_plant is None:
            self.food_check.set_inconsistent()
        else:
            self.food_check.set_active(meta.food_plant)
        
        if meta.poison_humans is None:
            self.poison_humans_check.set_inconsistent()
        else:
            self.poison_humans_check.set_active(meta.poison_humans)
        
        if meta.poison_animals is None:
            self.poison_animals_check.set_inconsistent()
        else:
            self.poison_animals_check.set_active(meta.poison_animals)

                        
    def _set_values_from_widgets(self):
        self.__values = {}
        #self.__values['__class__'] = self.table
        #values['distribution'] = self.dist_combo.get_active_text()
        it = self.dist_combo.get_active_iter()
        if it is not None:
            model = self.dist_combo.get_model()
            v = model.get_value(it, 0)
            self.__values['distribution'] = v
        
        if not self.food_check.get_inconsistent():
            self.__values['food_plant'] = self.food_check.get_active()
            
        if not self.poison_animals_check.get_inconsistent():
            self.__values['poison_animals'] = \
                self.poison_animals_check.get_active()
        
        if not self.poison_humans_check.get_inconsistent():
            self.__values['poison_humans'] = \
                self.poison_humans_check.get_active()
        
        # not values in self__values so set it to None so we don't create
        # empty objects
        if len(self.__values.keys()) == 0:
            self.__values = None
        
        
    def get_values(self):
        return _values
        
#        values = {}
#        values['__class__'] = self.table
#        #values['distribution'] = self.dist_combo.get_active_text()
#        it = self.dist_combo.get_active_iter()
#        model = self.dist_combo.get_model()
#        v = model.get_value(it, 0)
#        values['distribution'] = v
#        
#        
#        if not self.food_check.get_inconsistent():
#            values['food_plant'] = self.food_check.get_active()
#            
#        
#        if not self.poison_animals_check.get_inconsistent():
#            values['poison_animals'] = self.poison_animals_check.get_active()
#        
#        if not self.poison_humans_check.get_inconsistent():
#            values['poison_humans'] = self.poison_humans_check.get_active()
#        
#        return values
#    #values = property(_get_values)
        
    def __populate_distribution_combo(self):        
        # TODO: maybe i should just pickle the object out and read it back in
        # instead reading these from the database every time, it might be 
	# faster than querying the database but then again by sticking with
	# the database we're at least guaranteed some consistency with the rest
	# of the app
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
        self.dist_combo.set_model(model)
