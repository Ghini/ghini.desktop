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
from bauble.editor import TableEditorDialog
from bauble.utils.log import log, debug


    
    
class SpeciesMetaEditor(TableEditorDialog):
    
    standalone = False
    label = 'Species Meta'
    
    def __init__(self, select=None, defaults={}, **kwargs):
        super(SpeciesMetaEditor, self).__init__(tables["SpeciesMeta"], 
                                                'Species Meta Test', None,
                                                select, defaults, **kwargs)
        path = os.path.join(paths.lib_dir(), 'plugins', 'plants')
        self.glade_xml = gtk.glade.XML(path + os.sep + 'speciesmeta.glade')
        
        # override dialog from TableEditorDialog
#        self.dialog.destroy() # TODO: is this safe???
        #self.dialog = self.glade_xml.get_widget('main_dialog')
        window = self.glade_xml.get_widget('main_window')
        vbox = self.glade_xml.get_widget('main_box')
        window.remove(vbox)        	
        self.dialog = gtk.Dialog('Species Meta Editor', None,
                                 gtk.DIALOG_MODAL | \
                                 gtk.DIALOG_DESTROY_WITH_PARENT,
                                 (gtk.STOCK_OK, gtk.RESPONSE_OK, 
                                  gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    	self.dialog.set_resizable(False)
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
        values = self._get_values_from_widgets()
        if self.select is not None:
            values['id'] = self.select.id
        table_instance = self._commit(values)
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

                        
    def _get_values_from_widgets(self):
        values = {}
        #values['__class__'] = self.table
        #values['distribution'] = self.dist_combo.get_active_text()
        it = self.dist_combo.get_active_iter()
        if it is not None:
            model = self.dist_combo.get_model()
            v = model.get_value(it, 0)
            values['distribution'] = v
        
        if not self.food_check.get_inconsistent():
            values['food_plant'] = self.food_check.get_active()
            
        if not self.poison_animals_check.get_inconsistent():
            values['poison_animals'] = \
                self.poison_animals_check.get_active()
        
        if not self.poison_humans_check.get_inconsistent():
            values['poison_humans'] = \
                self.poison_humans_check.get_active()
        
        # not values in self__values so set it to None so we don't create
        # empty objects
        if len(values.keys()) == 0:
            values = None
	return values
                
        
    def __populate_distribution_combo(self):        
        # TODO: maybe i should just pickle the object out and read it back in
        # instead reading these from the database every time, it might be 
	# faster than querying the database but then again by sticking with
	# the database we're at least guaranteed some consistency with the rest
	# of the app
        model = gtk.TreeStore(str)
        model.append(None, ["Cultivated"])
        for continent in tables['Continent'].select():
            p1 = model.append(None, [str(continent)])
            for region in continent.regions:
                p2 = model.append(p1, [str(region)])
                for country in region.botanical_countries:
                    p3 = model.append(p2, [str(country)])
                    for unit in country.units:
                        if str(unit) != str(country):
                            model.append(p3, [str(unit)])            
        self.dist_combo.set_model(model)
