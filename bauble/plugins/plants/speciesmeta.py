#
# Species table definition
#
import os, traceback
import gtk
from sqlobject import *
import bauble.utils as utils
import bauble.paths as paths
from bauble.plugins import BaubleTable, tables, editors
from bauble.plugins.editor import TableEditor, ComboColumn
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
    species = ForeignKey('Species', default=None)
    
    
class SpeciesMetaEditor(TableEditor):
    
    #standalone = False
    label = 'Species Meta'
    
    def __init__(self, select=None, defaults={}):
        super(SpeciesMetaEditor, self).__init__(tables["SpeciesMeta"], 
                                                select, defaults)
        path = os.path.join(paths.lib_dir(), 'plugins', 'plants')
        self.glade_xml = gtk.glade.XML(path + os.sep + 'speciesmeta.glade')
        self.dialog = self.glade_xml.get_widget('main_dialog')
        self.dist_combo = self.glade_xml.get_widget('dist_combo')
        self._dirty=True
        self.committed = False
        self.food_check = self.glade_xml.get_widget('food_check')
        self.poison_animals_check =self.glade_xml.get_widget('poison_animals_check')            
        self.poison_humans_check =self.glade_xml.get_widget('poison_humans_check')
    
    def start(self):
        self._populate_distribution_combo()
        if self.select is not None:
            self._set_widget_values_from_instance(self.select)
            
        values = None
        response = gtk.RESPONSE_CANCEL
        while True:
            msg = 'Are you sure you want to lose your changes?'            
            response = self.dialog.run()
            if response == gtk.RESPONSE_OK:
                break
                #if self.dialog.run() == gtk.RESPONSE_OK:
                #    break
                #if self.commit_changes():
                #    break
            elif self._dirty and utils.yes_no_dialog(msg):
                break      
            else:
                break               
        values = self.get_values()
        self.dialog.destroy()
                
        return values
        
    #def on_dist_combo_changed(self, combo):
    #    self.dirty = True
    # TODO: should be able to have a common commit_changes for editors
    # and just do custom commits with hooks, since the class provides 
    # get_values there shouldn't really be any custom commits since your just
    # return the values you want to commit and the editor commits them
    def commit_changes(self):
        #values = self.get_values()
        
        print values
        if values is None: 
            return
        #conn = sqlhub.getConnection()
        #trans = conn.transaction()        
        trans = sqlhub.processConnection.transaction()
        #self.commited = None
        t = None
        try:
            debug('create table')
            # i guess the connection is inherant
            if self.select is None: # create a new table row
                t = self.table(connection=trans, **values)
            else: # update the table row passed in
                # TODO: if select and table aren't the same we should
                # ask the user if they want to change the type source
                if not isinstance(self.select, self.curr_editor.table):
                    msg = 'SourceEditor.commit_changes: the type has changed'
                    raise ValueError(msg)
                self.select.set(**values)
                t = self.select
                #raise NotImplementedError("TODO: updating a collection "\
                #                          "hasn't been implemented")
                #pass
            trans.commit()
            self.committed = t
        except Exception, e:
            msg = "SourcedEditor.commit_changes(): could not commit changes"
            utils.message_details_dialog(msg, traceback.format_exc(), 
                                         gtk.MESSAGE_ERROR)
            trans.rollback()
            return False        
        return True

    def _set_widget_values_from_instance(self, meta):
        #if meta.distribution is not None:
        #   pass
        if meta.food_plant is None:
            self.food_check.set_inconsistent()
        else:
            self.food_checl.set_active(meta.food_plant)
            
            
            
    def get_values(self):
        values = {}
        values['__class__'] = self.table
        #values['distribution'] = self.dist_combo.get_active_text()
        it = self.dist_combo.get_active_iter()
        model = self.dist_combo.get_model()
        v = model.get_value(it, 0)
        values['distribution'] = v
        
        
        if not self.food_check.get_inconsistent():
            values['food_plant'] = self.food_check.get_active()
            
        
        if not self.poison_animals_check.get_inconsistent():
            values['poison_animals'] = self.poison_animals_check.get_active()
        
        if not self.poison_humans_check.get_inconsistent():
            values['poison_humans'] = self.poison_humans_check.get_active()
        
        return values
        
        
    def _populate_distribution_combo(self):        
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