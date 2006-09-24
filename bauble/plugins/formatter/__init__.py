#
# formatter module
# 
#
#
# TODO: should make the search results sortable when clicking on the column 
# headers

# TODO: get the list of plants as an abcd lxml element tree and add 
# distribution data as a custom element so that the abcd builder doesn't create
# invalid abcd data

# TODO: all these formatter names are getting confusing, we should probably 
# rename the top level module to 'report' or something and report plugins
# could then be called 'formatters'

import os, sys, traceback
import gtk
from sqlalchemy import *
import lxml.etree as etree
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.prefs import prefs
from bauble.plugins import BaublePlugin, BaubleTool, plugins, tables
from bauble.utils.log import log, debug
import bauble.plugins.abcd as abcd

formatters_list_pref = 'formatter.formatters'  # name: formatter_class, formatter_kwargs
formatters_modules_pref = 'formatter.modules'
formatters_default_pref = 'formatter.default'
formatter_settings_expanded_pref = 'formatter.settings.expanded'

# TODO: need to make it so formatter plugins work if they are zipped up

# TODO: formatter tool menu item should have a drop down list so we can
# quickly select a formatter

def get_all_plants(objs):
    from bauble.plugins.garden.plant import Plant, plant_table
    all_plants = {}
    session = create_session()
    plant_query = session.query(Plant)
    
    def add_plants(plants):
        for p in plants:
            if id not in all_plants:
                all_plants[p.id] = p
    
    def get_plants_from_accessions(accessions):
        acc_ids = [acc.id for acc in accessions]
        plants = plant_query.select(Plant.c.id.in_(acc_ids))
        debug(plants)
        return plants
    
    for obj in objs:        
        debug(obj)
        # extract the plants from the search results
        # TODO: need to speed this up using custom queries, see the 
        # family and genera infoboxes
        if isinstance(obj, tables["Family"]):
            for gen in obj.genera:
                for sp in gen.species:
                    p = get_plants_from_accessions(sp.accessions)
                    add_plants(p)
        elif isinstance(obj, tables["Genus"]):
            for sp in obj.species:
                p = get_plants_from_accessions(sp.accessions)
                add_plants(p)
        elif isinstance(obj, tables["Species"]):
            p = get_plants_from_accessions(value.accessions)
            add_plants(p)
        elif isinstance(obj, tables["Accession"]):
            debug(obj.plants)
            add_plants(obj.plants)
        elif isinstance(obj, tables["Plant"]):
            add_plants([obj])
        elif isinstance(obj, tables["Location"]):
            add_plants(obj.plants)
        
    debug('all_plants: %s' % all_plants)
    return all_plants.values()



def _find_formatter_plugins():
    print '_find_module_names'
    names = []
    path, name = os.path.split(__file__)
    if path.find("library.zip") != -1: # using py2exe
        pkg = "bauble.plugins.formatter"
        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
        x = [zipfiles[file][0] for file in zipfiles.keys() if "bauble\\plugins\\formatter" in file]
        s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
        rx = re.compile(s.encode('string_escape'))
        for filename in x:
            m = rx.match(filename)
            if m is not None:
                names.append('%s.%s' % (pkg, m.group(1)))
    else:
        for d in os.listdir(path):
            full = path + os.sep + d
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                names.append(d)
                
    plugins = []
    for name in names:
        try:
            mod = __import__(name, globals(), locals(), ['formatter'])
        except Exception, e:
            msg = "Could not import the %s module." % name
            utils.message_details_dialog(msg, str(traceback.format_exc()), 
                     gtk.MESSAGE_ERROR)
            raise
        if hasattr(mod, "formatter"):
            plugins.append(mod.formatter)    
                
    return plugins 
    


class FormatterDialogView(object):
    
    def __init__(self):
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(),  
                                   "plugins", "formatter", 'formatter.glade'))
        self.dialog = self.widgets.formatter_dialog
        self.dialog.set_transient_for(bauble.app.gui.window)
        
        
    def start(self):
        return self.dialog.run()
        
        
        
class FormatterDialogPresenter(object):    
    
    formatter_class_map = {} # title->class map
    
    def __init__(self, view):    
        self.view = view
        self.init_names_combo()
        self.init_formatter_combo()

        self.view.widgets.new_button.connect('clicked', self.on_new_button_clicked)
        self.view.widgets.remove_button.connect('clicked', self.on_remove_button_clicked)
        self.view.widgets.names_combo.connect('changed', self.on_names_combo_changed)
        self.view.widgets.formatter_combo.connect('changed', self.on_formatter_combo_changed)
        self.view.widgets.ok_button.set_sensitive(False)
        
        # set the names combo to the default, on_names_combo_changes should 
        # do the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[formatters_default_pref]
        try:
            self.set_names_combo(default)
        except Exception, e:
            debug(e)
            self.set_names_combo(0)
                
                
    # TODO: i originally put these set_x_combo methods here b/c the 'changed'
    # signal wasn't being emitted when i called combo.set_active() but now
    # it seems to work alright....i don't know why this was happening
    def set_names_combo(self, val):
        '''
        set the names combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo
        '''
        combo = self.view.widgets.names_combo
        if isinstance(val, int):
            combo.set_active(val)    
        else:
            utils.combo_set_active_text(combo, val)
        #combo.emit('changed')        
        
        
    def set_formatter_combo(self, val):
        '''
        set the formatter combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo
        combo = self.view.widgets.formatter_combo
        '''
        combo = self.view.widgets.formatter_combo
        if isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)            
        #combo.emit('changed')
        
        
    def set_prefs_for(self, name, formatter_title, settings):
        '''
        this will overwrite any other formatter settings with name
        '''
        debug('set_prefs_for(%s, %s, %s)' % (name, formatter_title, settings))
        formatters = prefs[formatters_list_pref]
        try:
            debug('%s, %s' % (formatter_title, settings))
            formatters[name] = formatter_title, settings
        except AttributeError, e:
            debug(e)
            formatters[name] = None, None            
        prefs[formatters_list_pref] = formatters
    
                
    def on_new_button_clicked(self, *args):
        # TODO: don't set the OK button as sensitive in the name dialog
        # if the name already exists
        d = gtk.Dialog('', self.view.dialog,
                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))    
        d.vbox.set_spacing(10)
        label = gtk.Label('Enter a name for the new formatter')
        label.set_padding(10, 10)
        d.vbox.pack_start(label)    
        entry = gtk.Entry()
        d.vbox.pack_start(entry)    
        d.show_all()
        while True:
            if d.run() == gtk.RESPONSE_ACCEPT:
                name = entry.get_text()
                if name == '':
                    continue
                elif utils.tree_model_has(self.view.widgets.names_combo.get_model(), 
                                          name):
                    utils.message_dialog('%s already exists' % name)
                    continue
                else:
                    self.set_prefs_for(entry.get_text(), None, {})
                    break
            else:
                break
                
        d.destroy()
        self.populate_names_combo()
        utils.combo_set_active_text(self.view.widgets.names_combo, name)
            
    
    def on_remove_button_clicked(self, *args):
        formatters = prefs[formatters_list_pref]
        names_combo = self.view.widgets.names_combo
        name = names_combo.get_active_text()
        formatters.pop(name)
        prefs[formatters_list_pref] = formatters
        self.populate_names_combo()
        names_combo.set_active(0)

    
    def on_names_combo_changed(self, combo, *args):
        name = combo.get_active_text()
        debug('--- on_names_combo_changed(%s)' % name)
        formatters = prefs[formatters_list_pref]        
        self.view.widgets.details_box.set_sensitive(name is not None)
        prefs[formatters_default_pref] = name # set the default to the new name
        try:
            title, settings = formatters[name]
            debug('%s, %s' % (title, settings))
        except KeyError, e:
            debug(e)
            return
        
        try:
            self.set_formatter_combo(title)
        except Exception, e:
            debug(e)
            self.set_formatter_combo(-1)
            
        debug('--- leaving on_names_combo_changed()')
            
            
    def on_formatter_combo_changed(self, combo, *args):
        '''
        formatter_combo changed signal handler
        '''
        title = combo.get_active_text()                
        debug('**** on_formatter_combo_changed(%s)' % title)
        name = self.view.widgets.names_combo.get_active_text()        
        try:
            saved_title, settings = prefs[formatters_list_pref][name]            
            if saved_title != title:
                settings = {}                
            debug('settings: %s' % settings)
#            # set the new formatter value in the preferences
#            set_prefs_for(name, self.formatter_class_map[title])
#            #prefs[formatters_list_pref][name] = title, settings
        except KeyError, e:
            debug(e)
            return
        
        expander = self.view.widgets.settings_expander
        child = expander.get_child()
        if child is not None:
            expander.remove(child)
            
        self.widgets.ok_button.set_sensitive(title is not None)
        if title is None:
            return                    
        
        cls = self.formatter_class_map[title]
        box = cls.get_settings_box()
        if box is not None:
            box.update(settings)
            expander.add(box)
            box.show_all()            
        expander.set_sensitive(box is not None)     
        # TODO: should probably remember expanded state, 
        # see formatter_settings_expander_pref
        expander.set_expanded(box is not None)
        title = combo.get_active_text()        
        self.set_prefs_for(name, title, settings)
        debug('**** leaving on_formatter_combo_changed')
            
    
    def init_formatter_combo(self):        
        # - get list of previously added formatters from prefs
        # - check if there any formatters in the formatters directory that 
        # aren't in the list and add them if necessary
        module_path = os.path.join(paths.lib_dir(),  "plugins", "formatter")
        # walk this path looking for module with a __init__.py and provides
        # a formatter class        
        plugins = prefs[formatters_modules_pref]
        if plugins is None:
            plugins = []
        plugins.extend(_find_formatter_plugins())
        debug(plugins)
        model = gtk.ListStore(str)
        assert len(plugins) is not 0, 'No formatter plugins defined.'
#        if :
#            utils.message_dialog('No formatter plugins defined', gtk.MESSAGE_WARNING)
#            return
            
        for item in plugins:
            title = item.title
            self.formatter_class_map[title] = item            
            model.append([item.title])
        self.view.widgets.formatter_combo.set_model(model)        
        
        
    def populate_names_combo(self):    
        formatters = prefs[formatters_list_pref]
        combo = self.view.widgets.names_combo
        try:
            model = gtk.ListStore(str)
            for f in formatters.keys():
                model.append([f])
            combo.set_model(model)
        except AttributeError, e:
            # no formatters
            debug(e)
            pass
        
        
    def init_names_combo(self):                
        self.populate_names_combo()
        

    def save_formatter_settings(self):
        name = self.view.widgets.names_combo.get_active_text()        
        title, dummy =  prefs[formatters_list_pref][name]
        box = self.view.widgets.settings_expander.get_child()
        formatters = prefs[formatters_list_pref]
        debug('save_formatter_settings: %s: %s, %s' % (name, title, box.get_settings()))
        formatters[name] = title, box.get_settings()
        prefs[formatters_list_pref] = formatters
        debug(prefs[formatters_list_pref][name])
        
        
    def start(self):
        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response == gtk.RESPONSE_OK:
                debug('RESPONSE_OK')
                # get format method
                # save default
                prefs[formatters_default_pref] = self.view.widgets.names_combo.get_active_text()                
                self.save_formatter_settings()
                name = self.view.widgets.names_combo.get_active_text()        
                title, settings =  prefs[formatters_list_pref][name]
                formatter = self.formatter_class_map[title]
                break
            else:
                break
        self.view.dialog.destroy()
        return formatter, settings
        
    
     
class FormatterDialog(object):
    
    def __init__(self):        
        view = FormatterDialogView()
        self.presenter = FormatterDialogPresenter(view)


    def start(self):
        return self.presenter.start()
    
    
    
class FormatterTool(BaubleTool):    
    
    label = "Formatter"
    
    @classmethod
    def start(self):        
        '''
        '''    
        # get the select results from the search view
        import bauble
        view = bauble.app.gui.get_current_view()        
                        
        # TODO: this assumes a bit too much about SearchView's internal workings
        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog("Search for something first.")
            return
        
        bauble.app.set_busy(True)
        # extract the plants from the search results
        # TODO: need to speed this up using custom queries, see the 
        # family and genera infoboxes            
        try:
            dialog = FormatterDialog()
            formatter, settings = dialog.start()
            assert formatter is not None, 'No formatter'
            formatter.format([row[0] for row in model], **settings)
        except AssertionError, e:
            utils.message_dialog(str(e), gtk.MESSAGE_ERROR)
            debug(e)
        except Exception:
            debug(traceback.format_exc())
            utils.message_details_dialog('Formatting Error', 
                                     traceback.format_exc(), gtk.MESSAGE_ERROR)
        bauble.app.set_busy(False)       
        return



class FormatterPlugin(BaublePlugin):
    '''
    '''    
    tools = [FormatterTool]
    
        

plugin = FormatterPlugin        
    
