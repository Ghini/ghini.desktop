#
# formatter module
#
# this module should allow you to define a XSLT-FO formatter and and .fo file
# to process on the current selection
#
#
# TODO: should make the search results sortable when clicking on the column 
# headers

# TODO: get the list of plants as an abcd lxml element tree and add 
# distribution data as a custom element so that the abcd builder doesn't create
# invalid abcd data

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

# TODO: look for this on the path before starting anything and warn the use
# so they have a clue why the formatter isn't working
if sys.platform == "win32":
    fop_cmd = 'fop.bat'
else:
    fop_cmd = 'fop'
    
renderers_map = {'Apache FOP': fop_cmd + \
                 ' -fo %(fo_filename)s -pdf %(out_filename)s',
                 'XEP': 'xep -fo %(fo_filename)s -pdf %(out_filename)s',
#                 'xmlroff': 'xmlroff -o %(out_filename)s %(fo_filename)s',
#                 'Ibex for Java': 'java -cp /home/brett/bin/ibex-3.9.7.jar \
#		 ibex.Run -xml %(fo_filename)s -pdf %(out_filename)s'
                }

# TODO: what about creating a formatter package that can either be a zip or 
# directory with a __init__.py inside that sets the stylesheet and any other 
# options and manipulate the abcd if it chooses, could also pass a connection
# to the module so that it can make queries to the database if it chooses,
# preferably with read-only access

# TODO: if formatter chosen has any problems, i.e. the stylesheet file doesn't
# exis,  it would be good to desensitize the ok button and show a message in
# the status bar or something, then again we could wait until Ok is pressed 
# until we check for errors since we can't check if the fo renderer doesn't 
# exist

# TODO: it would probably make more sense to open up the FormatterOptions first
# and then whatever formatter is selected

# TODO: the default formatter should be a formatter module just like any other

# TODO: would probably also be useful to have a section in the options to 
# provide and advanced expander that a formatter module could provide or at
# least an entry where one could pass keyword=value, keyword1=value1 type 
# options to a formatter

# TODO: create a formatter named 'Default' where the only thing that can be 
# changed is the stylesheet

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


#def apply_stylesheet(stylesheet, xml):
#    '''
#    @param stylesheet: an ElementTree object that represents a valid XSL 
#    stylesheet
#    @param xml: and ElementTree object that represents the XML data to transform
#    @returns: 
#    '''
#    transform = etree.XSLT(stylesheet)
#    return transform(abcd_data)
    

def default_formatter():
    pass


#class Formatter:
#    
#    def __init__(self):
#        '''
#        the contructor
#        '''
#        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(), 
#                                   "plugins", "formatter", "formatter.glade"))
#        handlers = {'on_edit_button_clicked': self.on_edit_button_clicked,
#                   }        
#        self.widgets.signal_autoconnect(handlers)        
#        self.formatter_dialog = self.widgets.formatter_dialog
#        self.formatter_dialog.set_transient_for(bauble.app.gui.window)
#        self.formatters_combo = self.widgets.formatters_combo
#        self.treeview = self.widgets.treeview
#        
#        
#    def do_win32_fixes(self):
#        '''
#        '''
#        import pango
#        def get_char_width(widget):
#            context = widget.get_pango_context()        
#            font_metrics = context.get_metrics(context.get_font_description(), 
#                                               context.get_language())        
#            width = font_metrics.get_approximate_char_width()            
#            return pango.PIXELS(width)
#
#        formatters_combo = self.widgets.formatters_combo
#        formatters_combo.set_size_request(get_char_width(formatters_combo)*20, -1)
#        
#        
#    def start(self, plants):
#        '''
#        @param plants: the plants to format
#        '''
#        if sys.platform == 'win32':
#            self.do_win32_fixes()
#            
#        self.populate_tree(plants)        
#        # TODO: check if there are formatters defined and if not then ask
#        # the user if they would like to create one now, this might be 
#        # something we can 
#        self.populate_formatters_from_prefs()
#        formatters = prefs[formatters_list_pref]
#        if formatters is None:
#            fo = FormatterOptions(parent=self.formatter_dialog)
#            fo.start()
#                
#        # get formatters again in case FormatterOptions changed anything
#        #formatters = prefs[formatters_list_pref]
#        #if formatters is None:
#        #    self.formatters_combo.set_sensitive(False)
#            # TODO: should also set OK button as not sensitive
#            
#        default = prefs[formatters_default_pref]
#        if default is not None and default in formatters:
#            utils.set_combo_from_value(self.formatters_combo, default)
#            #combo_set_active_text(self.formatters_combo, default)
#        
#        pdf_filename = None
#        
#        try:
#            if self.formatter_dialog.run() == gtk.RESPONSE_OK:
#                # refresh formatters in case they change in the options and set
#                # the default
#                formatters = prefs[formatters_list_pref]
#                active = self.formatters_combo.get_active_text()
#                prefs[formatters_default_pref] = active
#                # TODO: should we make sure the stylesheet exists first?
#                stylesheet = formatters[active]['stylesheet'] 
#                fo_cmd = renderers_map[formatters[active]['renderer']]
#                pdf_filename = self.create_pdf(fo_cmd, stylesheet)
#        finally:
#            self.formatter_dialog.destroy()        
#        
#        return pdf_filename
#        
#    
#    def format(self):
#        # find out what we need to do and do it, either by calling the default
#        # formatter or by calling the formatter module
#        pass
#    
#    
#    def create_pdf(self, fo_cmd, stylesheet, filename=None):
#        '''
#        returns the filename of a new pdf file
#        @param fo_cmd: e.g fop -fo %(fo_filename)s -pdf %(out_filename)s'
#        @param stylesheet: the filename of an xsl stylesheet to apply to the 
#            data, this file is what determines the formatting
#        @param filename: the output filename, if filename is None(the default) 
#            then a random temporary file will be created
#        '''
#        import tempfile
#        if filename is None:
#            # no filename, create a temporary file            
#            dummy, filename = tempfile.mkstemp()                
#            filename += ".pdf"
#        
#        # get all the plants from the model in ABCD format
#        plants = []
#        for yes_no, plant in self.treeview.get_model():
#            if yes_no:
#                plants.append(plant)
#            
##        debug(plants)
#        abcd_data = abcd.plants_to_abcd(plants)    
#        # TODO: add 
#        # for each dataset
#        #     for each unit
#        #        get the plant.id this refers to
#        #        add a distribution to unit
#                
#        # create xsl fo file
#        dummy, fo_filename = tempfile.mkstemp()
#        style_doc = etree.parse(stylesheet)
#        result = apply_stylesheet(style_doc)
#        outfile = open(fo_filename, 'w')
#        outfile.write(unicode(result))
#        outfile.close()
#        
#        # run the formatter to produce the pdf file, xep has to be on the
#        # path
#        fo_cmd = fo_cmd % ({'fo_filename': fo_filename, 
#                            'out_filename': filename})
#	
#	# TODO: 
#	# 1: get exit code with waiting for the process the finish/block
#	# 2. popup progress dialog
#	# 3. read stdout and stderr if didn't exit with 0
#	# 4. i don't know how to get all these
#        os.system(fo_cmd)    	
#        
##        d = gtk.Dialog('Output', None, 
##                       flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
##                       buttons=((gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)))
##
##        tb = gtk.TextBuffer()
##        textview = gtk.TextView(tb)
##        d.vbox.pack_start(textview)
##        textview.show()
##        for line in stdout_err.readlines():
##            tb.insert_at_cursor(line)
##        d.run()
##        d.destroy()
#            
#        # open and return the file hander or filename so we don't have to close it
#        return filename    
#
#
#    def populate_formatters_from_prefs(self):
#        '''
#        '''
#        model = gtk.ListStore(str)
#        formatters = prefs[formatters_list_pref]
#        if formatters is None:
#            self.formatters_combo.set_sensitive(False)
#            return
#        
#        self.formatters_combo.set_sensitive(True)
#        for i in sorted(formatters.keys()):
#            model.append([i])
#        self.formatters_combo.set_model(model)        
#                
#        
#    def build_gui(self):
#        '''
#        '''
#        self.dialog = gtk.Dialog('Formatter', bauble.app.gui.window,
#                                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
#                                 buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
#                                           gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))
#        hbox = gtk.HBox()
#        self.dialog.vbox.pack_start(hbox)
#        
#        
#    def on_edit_button_clicked(self, widget):
#        '''
#        '''
#        active = self.formatters_combo.get_active_text()        
#        fo = FormatterOptions(active, parent=self.formatter_dialog)
#        fo.start()
#        self.populate_formatters_from_prefs()
#        utils.set_combo_from_value(self.formatters_combo, active)
#        #combo_set_active_text(self.formatters_combo, active)
#        
#        
#    def name_cell_data_method(self, column, cell, model, iter, data=None):
#        '''
#        '''
#        plant = model.get_value(iter, 1)
#        cell.set_property('text', str(plant.accession.species))
#        
#        
#    def id_cell_data_method(self, column, cell, model, iter, data=None):
#        '''
#        '''
#        plant = model.get_value(iter, 1)
#        cell.set_property('text', str(plant))    
#        
#    
#    def toggle_cell_data_method(self, column, cell, model, iter, data=None):
#        '''
#        '''
#        value = model.get_value(iter, 0)
#        #debug(iter)
#        if value is None:
#            # this should really get the default value from the table
#            #debug('inconsistent')
#            cell.set_property('inconsistent', False) 
#        else:
#            #debug('active: ' + str(value))
#            cell.set_property('active', value)
#        
#        
#    def on_renderer_toggled(self, widget, path, model):
#        '''
#        '''
#        active = widget.get_active()
#        #model = self.plants_view.get_model()
#        it = model.get_iter(path)
#        model.set_value(it, 0, not active)
#        
#        
#    def populate_tree(self, plants):
#        '''
#        '''
#        model = gtk.ListStore(bool, object)
#        for p in plants:
#        
#            model.append([True, p])
#        tree_view = self.widgets.treeview
#        
#        toggle_ren = gtk.CellRendererToggle()       
#        toggle_ren.connect("toggled", self.on_renderer_toggled, model) 
#        toggle_col = gtk.TreeViewColumn(None, toggle_ren)
#        toggle_col.set_cell_data_func(toggle_ren, self.toggle_cell_data_method)
#        tree_view.append_column(toggle_col)
#        
#        id_ren = gtk.CellRendererText()
#        id_col = gtk.TreeViewColumn('ID', id_ren)
#        id_col.set_cell_data_func(id_ren, self.id_cell_data_method, 'id')
#        tree_view.append_column(id_col)
#        
#        name_ren = gtk.CellRendererText()
#        name_col = gtk.TreeViewColumn('Name', name_ren)
#        name_col.set_cell_data_func(name_ren, self.name_cell_data_method)
#        tree_view.append_column(name_col)
#        
#        tree_view.set_model(model)
#            
#            
#            
#class FormatterOptions:
#    '''
#    '''
#    
#    def __init__(self, active_formatter=None, parent=None):
#        '''
#        active_formatter is the formatter we should set as active for editing
#        '''        
#        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(), 
#                                   "plugins", "formatter", 'formatter.glade'))
#        self.dialog = self.widgets.formatter_options_dialog
#        if parent is not None:            
#            self.dialog.set_transient_for(parent)
#        else:
#            self.dialog.set_transient_for(bauble.app.gui.window)
#        
#        self.remove_button = self.widgets.remove_button
#        self.remove_button.set_sensitive(False)    
#        self.formatters_combo = self.widgets.opt_formatters_combo
#        self.formatter_chooser = self.widgets.formatter_chooser
#        
#        # setup renderers combo
#        self.renderers_combo = self.widgets.renderers_combo        
#        model = gtk.ListStore(str)
#        for r in sorted(renderers_map.keys()):
#            model.append([r])
#        self.renderers_combo.set_model(model)
#        self.renderers_combo.set_sensitive(False)
#        
#        
#        
#        handlers = {'on_new_button_clicked': self.on_new_button_clicked,
#                    'on_remove_button_clicked': self.on_remove_button_clicked,
#        }
#        self.widgets.signal_autoconnect(handlers)
#        
#        # populate the formatters combo with all the formatter names
#        formatters = prefs[formatters_list_pref]
#        if formatters is not None:        
#            model = gtk.ListStore(str)
#            self.formatters_combo.set_model(model)
#            for f in sorted(formatters.keys()):
#                self.formatters_combo.append_text(f)
#                
#            # TODO: should set the default and if there no default then select
#            # the first one in the list
#            self.formatters_combo.set_active(0)
#                
#        self.refresh_view()
#    
#        # now that the view has been refreshed connect the signal handlers
#        # for the formatter_chooser and renderers_combo to watch for any changes        
#        self.renderers_combo.connect('changed', self.on_changed_formatter_prefs)                
#        self.formatter_chooser.connect('current-folder-changed', 
#                                       self.on_changed_formatter_prefs)
#    
#    
#    def start(self):
#        '''
#        open the formatter options
#        '''        
#        self.dialog.run()            
#        self.dialog.destroy()
#    
#        
#    def refresh_sensitivity(self):
#        '''
#        set the sensitivity of options dialog according to the values
#        in the widgets
#        '''
##        debug('refresh_sensitivity()')
#        formatter, renderer = None, None
#        try:
#            formatter, renderer = self.get_active_formatter()
##            debug('%s, %s' % (formatter, renderer))
#        except KeyError, e:
#            raise NameError('Couldn\'t find preferences for a formatter with '\
#                            'name %s' % name)
#        close_button = self.widgets.options_close_button
#        if os.path.isdir(formatter) or formatter[-4:] == '.zip': 
#            self.renderers_combo.set_sensitive(False)
#            close_button.set_sensitive(True)
##            debug('sensitivity: False, True')
#        else:
#            self.renderers_combo.set_sensitive(True)
#            debug(renderer is not None)
#            close_button.set_sensitive(renderer is not None)
##            debug('sensitivity: True, %s' % renderer is None)
#    
#        self.remove_button.set_sensitive(self.formatters_combo.get_model() > 0)
#        
#
#    def refresh_view(self):
#        '''
#        get the values from the prefs and set the widgets accordingly
#        '''
##        debug('refresh_view()')
#        formatter, renderer = None, None
#        try:
#            formatter, renderer = self.get_active_formatter()
##            debug('%s, %s' % (formatter, renderer))
#        except KeyError, e:
#            utils.message_details_dialog('Couldn\'t get formatter settings.\n\n'\
#                                         '%s' % str(e), traceback.format_exc())
#            #raise NameError('Couldn\'t find preferences for a formatter with '\
#            #                'name %s' % name)
#                    
#        try:
#            self.formatter_chooser.set_filename(formatter)
#        except TypeError, e:
#            self.formatter_chooser.set_current_name('Choose a file...')
#            
#        try:
#            utils.set_combo_from_value(self.renderers_combo, renderer)
#        except:
#            self.renderers_combo.set_active(-1)
#        self.refresh_sensitivity()
##        debug('leaving refresh_view()')
#        
#        
#    def on_new_button_clicked(self, widget):
#        '''
#        '''
#        # TODO: don't set the OK button as sensitive in the name dialog
#        # if the name already exists
#        d = gtk.Dialog('New Formatter Name', self.dialog,
#                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
#                       buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
#                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))    
#        d.vbox.set_spacing(10)
#        label = gtk.Label('Enter a name for the new formatter')
#        label.set_padding(10, 10)
#        d.vbox.pack_start(label)    
#        entry = gtk.Entry()
#        d.vbox.pack_start(entry)    
#        d.show_all()
#        while True:
#            if d.run() == gtk.RESPONSE_ACCEPT:
#                name = entry.get_text()            
#                model = self.formatters_combo.get_model()
#                if name == '':
#                    continue
#                elif utils.tree_model_has(model, name):
#                    utils.message_dialog('%s already exists' % name)
#                    continue
#                else:
#                    self.add_formatter(entry.get_text())
#                    break
#            else:
#                break
#                
#        d.destroy()
#        self.refresh_view()
#            
#
#    def on_remove_button_clicked(self, widget):        
#        '''
#        '''        
#        # should only be ble to click remove if there is a formatter selected
#        name = self.formatters_combo.get_active_text()
#        msg = 'Are you sure you want to remove "%s"?' % name
#        if utils.yes_no_dialog(msg):            
#            # remove the formatter from the formatters_combo model and set 
#            # current to -1 so that on_formatters_combo_changed will be called
#            model = self.formatters_combo.get_model()
#            it = self.formatters_combo.get_active_iter()
#            model.remove(it)
#            self.formatters_combo.set_active(-1)
#        
#            # remove the formatter from the prefs
#            formatters = prefs[formatters_list_pref]
#            del formatters[name]
#            prefs[formatters_list_pref] = formatters
#            self.refresh_view()
#            #self.refresh_active_formatter_options()
#        
#            
#    def on_formatters_combo_changed(self, combo):
#        '''
#        '''        
#        self.refresh_view()
##        self.refresh_active_formatter_options()
##        if combo.get_active() == -1:
##            self.remove_button.set_sensitive(False)
##        else:
##            self.remove_button.set_sensitive(True)
#    
#            
#    def add_formatter(self, name, formatter=None, renderer=None):
#        '''
#        add a formatter with name to formatter in the prefs, the renderer and
#        stylesheet both default to None
#        '''
#        formatters = prefs[formatters_list_pref]
#        if formatters is None:
#            formatters = {}
#        if name in formatters:            
#            utils.message_dialog('A formatter with this name already exists')
#        else:
#            formatters[name] = formatter, renderer
#        prefs[formatters_list_pref] = formatters
#        model = self.formatters_combo.get_model()
#        it = model.append([name])
#        self.formatters_combo.set_active_iter(it)
#        
#        
#    def on_changed_formatter_prefs(self, widget, *args):
#        '''
#        on of the formatter prefs changed, get the values from the dialog
#        and set them in the prefs
#        '''
##        debug('on_changed_formatter_prefs: %s' % widget)
#        
#        chosen = self.formatter_chooser.get_filename()
#        if chosen is None:
#            return # don't change anything....this is a corner case
#        dir, filename = os.path.split(chosen)
#        if filename == '__init__.py':            
#            formatter = dir
#            #self.formatter_chooser.set_filename(dir)
#            #self.formatter_chooser.set_title(dir)
#            renderer = None
#        elif filename[:-4] == '.zip': 
#            formatter = chosen
#            renderer = None
#        else:
#            formatter = chosen
#            renderer = self.renderers_combo.get_active_text()
#
#        self.set_active_formatter_prefs(formatter, renderer)
#        
#        self.refresh_sensitivity()
#        
#        
#    def set_active_formatter_prefs(self, formatter, renderer=None):
#        '''
#        set formatter and renderer of active formatter
#        '''
#        name = self.get_active_formatter_name()
#        formatters = prefs[formatters_list_pref]
#        try:
#            formatters[name] = formatter, renderer
#            prefs[formatters_list_pref] = formatters
#        except KeyError, e:
#            # TODO: should i create a formatter with this name then???
#            raise KeyError('Couldn\'t get formatter from the prefs called %s' \
#                           %name)
#        
#        
#    def get_active_formatter(self):
#        '''
#        get the formatter prefs for the active formatter
#        '''
#        name = self.get_active_formatter_name()
#        return prefs[formatters_list_pref][name]
#
#
#    def get_active_formatter_name(self):
#        '''
#        get the name of the current formatter
#        '''
#        return self.formatters_combo.get_active_text()

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
    


#def _find_modules():
#    
#    module_names = _find_module_names()
#    # import the modules and test if they provide a plugin to make sure 
#    # they are plugin modules    
#    modules = []
#    for name in module_names:
#        try:
#            mod = __import__(name, globals(), locals(), ['formatter'])
#        except Exception, e:
#            msg = "Could not import the %s module." % name
#            utils.message_details_dialog(msg, str(traceback.format_exc()), 
#                     gtk.MESSAGE_ERROR)
#            raise
#        if hasattr(mod, "format"):
#            modules.append(mod)
#            #formatters.append(mod.formatter)    
#    #return formatters
#    return modules

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
        #self.refresh_view()

        self.view.widgets.new_button.connect('clicked', self.on_new_button_clicked)
        self.view.widgets.remove_button.connect('clicked', self.on_remove_button_clicked)
        self.view.widgets.names_combo.connect('changed', self.on_names_combo_changed)
        self.view.widgets.formatter_combo.connect('changed', self.on_formatter_combo_changed)
        
        # set the names combo to the default, on_names_combo_changes should 
        # do the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[formatters_default_pref]
        try:
            self.set_names_combo(default)
        except Exception, e:
            debug(e)
            self.set_names_combo(0)
                
                
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
        #utils.combo_set_active_text(self.view.widgets.names_combo, name)
        self.refresh_view()
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
        dialog = FormatterDialog()       
        try:
            formatter, settings = dialog.start()
            formatter.format([row[0] for row in model], **settings)
        except Exception:
            debug(traceback.format_exc())
            utils.message_details_dialog('Formatting Error', 
                                     traceback.format_exc(), gtk.MESSAGE_ERROR)            
        bauble.app.set_busy(False)       
        return
    
#        plants = get_all_plants([row[0] for row in model])
#            
#        if len(plants) == 0:
#            utils.message_dialog('There are no plants in the search '\
#                                 'results. Please try another search.')
#            bauble.app.set_busy(False)
#            return
#        
#        formatter = Formatter()    
#        try:            
#            pdf_filename = formatter.start(plants)
#        except:
#            msg = 'Could not create PDF file.'
#            utils.message_details_dialog(msg, traceback.format_exc(), 
#                                         gtk.MESSAGE_ERROR)
#        else:
#            if pdf_filename is not None:            
#                utils.startfile(pdf_filename)
#        bauble.app.set_busy(False)       
#class FormatterTool(BaubleTool):    
#    label = "Formatter"
#    
#    @classmethod
#    def start(self, objects):        
#        '''
#        '''    
#        # get all of the current plants from the view
#        import bauble
#        view = bauble.app.gui.get_current_view()        
#
##        if not isinstance(view, bauble.plugins.searchview.search.SearchView):
##            raise Error('Formmatter: can only format results from the '\
##                        'search vew')
#                        
#        # TODO: this assumes a bit too much about SearchView's internal workings
#        model = view.results_view.get_model()
#        if model is None:
#            utils.message_dialog("Search for something first.")
#            return
#        
#        bauble.app.set_busy(True)
#        # extract the plants from the search results
#        # TODO: need to speed this up using custom queries, see the 
#        # family and genera infoboxes
#        plants = get_all_plants([row[0] for row in model])
#            
#        if len(plants) == 0:
#            utils.message_dialog('There are no plants in the search '\
#                                 'results. Please try another search.')
#            bauble.app.set_busy(False)
#            return
#        
#        formatter = Formatter()    
#        try:            
#            pdf_filename = formatter.start(plants)
#        except:
#            msg = 'Could not create PDF file.'
#            utils.message_details_dialog(msg, traceback.format_exc(), 
#                                         gtk.MESSAGE_ERROR)
#        else:
#            if pdf_filename is not None:            
#                utils.startfile(pdf_filename)
#        bauble.app.set_busy(False)       
    
    
    
class FormatterPlugin(BaublePlugin):
    '''
    '''    
    tools = [FormatterTool]
    depends = ["ABCDImexPlugin"]
    
    try:
        import lxml
    except ImportError: 
        FormatterTool.enabled = False
        debug(traceback.format_exc())        
        

plugin = FormatterPlugin        
    
