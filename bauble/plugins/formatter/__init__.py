#
# formatter module
#
# this module should allow you to define a XSLT-FO formatter and and .fo file
# to process on the current selection
#
#
# TODO: should make the search results sortable when clicking on the column 
# headers

import os, sys, traceback
import gtk
import bauble
import bauble.utils as utils
import bauble.paths as paths
from bauble.prefs import prefs
from bauble.plugins import BaublePlugin, BaubleTool, plugins, tables
from bauble.utils.log import log, debug
from bauble.plugins.imex_abcd import abcd
    
formatters_list_pref = 'formatter.formatters'    
formatters_default_pref = 'formatter.default'

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

# TODO: if formatter chosen has any problems, i.e. the stylesheet file doesn't
# exis,  it would be good to desensitize the ok button and show a message in
# the status bar or something, then again we could wait until Ok is pressed 
# until we check for errors since we can't check if the fo renderer doesn't 
# exist

# TODO: this could probably go in bauble.utils
# UPDATE: utils.set_combo_from_value does essentially the same thing but I don't
# want to switch it just now without testing it maybe for version 0.5.2+
def combo_set_active_text(combo, text):
    model = combo.get_model()
    for row in model:
        if row[0] == text:            
            combo.set_active_iter(row.iter)
            return
    raise ValueError('%s is not a valid value in combo' % text)


class Formatter:
    
    def __init__(self):
        '''
        the contructor
        '''
        path = os.path.join(paths.lib_dir(), "plugins", "formatter")
        self.glade_xml = gtk.glade.XML(path + os.sep + "formatter.glade")
        handlers = {'on_edit_button_clicked': self.on_edit_button_clicked,
                   }
        self.glade_xml.signal_autoconnect(handlers)
        
        self.formatter_dialog = self.glade_xml.get_widget('formatter')        
        self.formatters_combo = self.glade_xml.get_widget('formatters_combo')
        self.treeview = self.glade_xml.get_widget('treeview')
        
        
    def do_win32_fixes(self):
        '''
        '''
        import pango
        def get_char_width(widget):
            context = widget.get_pango_context()        
            font_metrics = context.get_metrics(context.get_font_description(), 
                                               context.get_language())        
            width = font_metrics.get_approximate_char_width()            
            return pango.PIXELS(width)

        formatters_combo = self.glade_xml.get_widget('formatters_combo')
        formatters_combo.set_size_request(get_char_width(formatters_combo)*20, -1)
        
        
    def start(self, plants):
        '''
        @param plants: the plants to format
        '''
        if sys.platform == 'win32':
            self.do_win32_fixes()
            
        self.populate_tree(plants)        
        # TODO: check if there are formatters defined and if not then ask
        # the user if they would like to create one now, this might be 
        # something we can 
        self.populate_formatters_from_prefs()
        formatters = prefs[formatters_list_pref]
        if formatters is None:
            fo = FormatterOptions()
            fo.start()
                
        # get formatters again in case FormatterOptions changed anything
        #formatters = prefs[formatters_list_pref]
        #if formatters is None:
        #    self.formatters_combo.set_sensitive(False)
            # TODO: should also set OK button as not sensitive
            
        default = prefs[formatters_default_pref]
        if default is not None and default in formatters:
            combo_set_active_text(self.formatters_combo, default)
        
        pdf_filename = None
        
        try:
            if self.formatter_dialog.run() == gtk.RESPONSE_OK:
                # refresh formatters in case they change in the options and set
                # the default
                formatters = prefs[formatters_list_pref]
                active = self.formatters_combo.get_active_text()
                prefs[formatters_default_pref] = active
                # TODO: should we make sure the stylesheet exists first?
                stylesheet = formatters[active]['stylesheet'] 
                fo_cmd = renderers_map[formatters[active]['renderer']]
                pdf_filename = self.create_pdf(fo_cmd, stylesheet)
        finally:
            self.formatter_dialog.destroy()        
        
        return pdf_filename
        

    def create_pdf(self, fo_cmd, stylesheet, filename=None):
        '''
        returns the filename of a new pdf file
        @param fo_cmd: e.g fop -fo %(fo_filename)s -pdf %(out_filename)s'
        @param stylesheet: the filename of an xsl stylesheet to apply to the 
            data, this file is what determines the formatting
        @param filename: the output filename, if filename is None(the default) 
            then a random temporary file will be created
        '''
        import libxml2
        import libxslt
        import tempfile
        if filename is None:
            # no filename, create a temporary file            
            dummy, filename = tempfile.mkstemp()                
            filename += ".pdf"
        
        # get all the plants from the model in ABCD format
        plants = []
        for yes_no, plant in self.treeview.get_model():
            if yes_no:
                plants.append(plant)
            
        abcd_data = abcd.plants_to_abcd(plants)    
                
        # create xsl fo file
        dummy, fo_filename = tempfile.mkstemp()
        #xslt_filename = os.path.dirname(__file__) + os.sep + 'label.xsl'
#        debug(xslt_filename)
        # how come we don't have to free style_doc???
        style_doc = libxml2.parseFile(stylesheet) 
        style = libxslt.parseStylesheetDoc(style_doc)
        doc = libxml2.parseDoc(abcd_data)
        result = style.applyStylesheet(doc, None)
        style.saveResultToFilename(fo_filename, result, 0)
        style.freeStylesheet()
        doc.freeDoc()
        result.freeDoc()
        
        # run the formatter to produce the pdf file, xep has to be on the
        # path
        fo_cmd = fo_cmd % ({'fo_filename': fo_filename, 
                            'out_filename': filename})
	
	# TODO: 
	# 1: get exit code with waiting for the process the finish/block
	# 2. popup progress dialog
	# 3. read stdout and stderr if didn't exit with 0
	# 4. i don't know how to get all these
        os.system(fo_cmd)    	
        
#        d = gtk.Dialog('Output', None, 
#                       flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
#                       buttons=((gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)))
#
#        tb = gtk.TextBuffer()
#        textview = gtk.TextView(tb)
#        d.vbox.pack_start(textview)
#        textview.show()
#        for line in stdout_err.readlines():
#            tb.insert_at_cursor(line)
#        d.run()
#        d.destroy()
            
        # open and return the file hander or filename so we don't have to close it
        return filename    


    def populate_formatters_from_prefs(self):
        '''
        '''
        model = gtk.ListStore(str)
        formatters = prefs[formatters_list_pref]
        if formatters is None:
            self.formatters_combo.set_sensitive(False)
            return
        
        self.formatters_combo.set_sensitive(True)
        for i in sorted(formatters.keys()):
            model.append([i])
        self.formatters_combo.set_model(model)
                
        
    def build_gui(self):
        '''
        '''
        self.dialog = gtk.Dialog('Formatter', bauble.app.gui.window,
                                 flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                                 buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                           gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))
        hbox = gtk.HBox()
        self.dialog.vbox.pack_start(hbox)
        
        
    def on_edit_button_clicked(self, widget):
        '''
        '''
        active = self.formatters_combo.get_active_text()        
        fo = FormatterOptions(active)
        fo.start()
        self.populate_formatters_from_prefs()
        combo_set_active_text(self.formatters_combo, active)
        
        
    def name_cell_data_method(self, column, cell, model, iter, data=None):
        '''
        '''
        plant = model.get_value(iter, 1)
        cell.set_property('text', str(plant.accession.species))
        
        
    def id_cell_data_method(self, column, cell, model, iter, data=None):
        '''
        '''
        plant = model.get_value(iter, 1)
        cell.set_property('text', str(plant))    
        
    
    def toggle_cell_data_method(self, column, cell, model, iter, data=None):
        '''
        '''
        value = model.get_value(iter, 0)
        #debug(iter)
        if value is None:
            # this should really get the default value from the table
            #debug('inconsistent')
            cell.set_property('inconsistent', False) 
        else:
            #debug('active: ' + str(value))
            cell.set_property('active', value)
        
        
    def on_renderer_toggled(self, widget, path, model):
        '''
        '''
        active = widget.get_active()
        #model = self.plants_view.get_model()
        it = model.get_iter(path)
        model.set_value(it, 0, not active)
        
        
    def populate_tree(self, plants):
        '''
        '''
        model = gtk.ListStore(bool, object)
        for p in plants:
        
            model.append([True, p])
        tree_view = self.glade_xml.get_widget('treeview')
        
        toggle_ren = gtk.CellRendererToggle()       
        toggle_ren.connect("toggled", self.on_renderer_toggled, model) 
        toggle_col = gtk.TreeViewColumn(None, toggle_ren)
        toggle_col.set_cell_data_func(toggle_ren, self.toggle_cell_data_method)
        tree_view.append_column(toggle_col)
        
        id_ren = gtk.CellRendererText()
        id_col = gtk.TreeViewColumn('ID', id_ren)
        id_col.set_cell_data_func(id_ren, self.id_cell_data_method, 'id')
        tree_view.append_column(id_col)
        
        name_ren = gtk.CellRendererText()
        name_col = gtk.TreeViewColumn('Name', name_ren)
        name_col.set_cell_data_func(name_ren, self.name_cell_data_method)
        tree_view.append_column(name_col)
        
        tree_view.set_model(model)
            
            
            
class FormatterOptions:
    '''
    '''
    
    def __init__(self, active_formatter=None):
        '''
        active_formatter is the formatter we should set as active for editing
        '''
        path = os.path.join(paths.lib_dir(), "plugins", "formatter")
        self.glade_xml = gtk.glade.XML(path + os.sep + 'formatter.glade')
        self.formatters_combo=self.glade_xml.get_widget('opt_formatters_combo')
        
        self.remove_button = self.glade_xml.get_widget('remove_button')
        self.remove_button.set_sensitive(False)
        
        self.renderers_combo = self.glade_xml.get_widget('renderers_combo')
        model = gtk.ListStore(str)
        for r in sorted(renderers_map.keys()):
            model.append([r])
        self.renderers_combo.set_model(model)
        self.renderers_combo.set_sensitive(False)
    
        # create the stylesheet chooseer button
        fcd = gtk.FileChooserDialog(action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                    buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                        gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        fcd.connect('response', self.on_stylesheet_button_response)
        self.stylesheet_button = gtk.FileChooserButton(fcd)
        table = self.glade_xml.get_widget('options_table')
        table.attach(self.stylesheet_button, 1, 2, 1, 2, 
                     xoptions=gtk.EXPAND|gtk.FILL, yoptions=0)
        self.stylesheet_button.show()
        
        handlers = {'on_new_button_clicked': self.on_new_button_clicked,
                    'on_remove_button_clicked': self.on_remove_button_clicked,
                    'on_opt_formatters_combo_changed': 
                        self.on_formatters_combo_changed,
                    'on_renderers_combo_changed': 
                        self.on_renderers_combo_changed}
        self.glade_xml.signal_autoconnect(handlers)
        
        formatters = prefs[formatters_list_pref]
        if formatters is not None:        
            model = gtk.ListStore(str)
            self.formatters_combo.set_model(model)
            for f in sorted(formatters.keys()):
                self.formatters_combo.append_text(f)
            self.formatters_combo.set_active(0)
    
        if active_formatter is not None:
            combo_set_active_text(self.formatters_combo, active_formatter)
    
    
    def start(self):
        '''
        '''
        d = self.glade_xml.get_widget('options_dialog')
        d.run()            
        d.destroy()
        
    
    def on_new_button_clicked(self, widget):
        '''
        '''
        d = gtk.Dialog('Enter a name for the formatter', bauble.app.gui.window,
                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))    
        entry = gtk.Entry()
        entry.show()
        d.vbox.pack_start(entry)    
        if d.run() == gtk.RESPONSE_ACCEPT:
            name = entry.get_text()            
            model = self.formatters_combo.get_model()
            if name != '' and not FormatterOptions.in_model(model, name):
                self.add_formatter(entry.get_text())
        d.destroy()
            

    def on_remove_button_clicked(self, widget):        
        '''
        '''        
        # should only be ble to click remove if there is a formatter selected
        name = self.formatters_combo.get_active_text()
        msg = 'Are you sure you want to remove the %s formatter?' % name
        if utils.yes_no_dialog(msg):            
            # remove the formatter from the formatters_combo model and set 
            # current to -1 so that on_formatters_combo_changed will be called
            model = self.formatters_combo.get_model()
            it = self.formatters_combo.get_active_iter()
            model.remove(it)
            self.formatters_combo.set_active(-1)
        
            # remove the formatter from the prefs
            formatters = prefs[formatters_list_pref]
            del formatters[name]
            prefs[formatters_list_pref] = formatters
            
            self.refresh_active_formatter_options()
        
    
    def on_renderers_combo_changed(self, combo):
        '''
        '''
        renderer = combo.get_active_text()
        if renderer is not None:
            self.set_active_formatter_renderer_in_prefs(renderer)
            combo.set_sensitive(True)
        
    
    def on_stylesheet_button_response(self, dialog, response):        
        '''
        '''
        if response != gtk.RESPONSE_ACCEPT:
            return
        filename = dialog.get_filename()
        self.stylesheet_button.set_filename(filename)
        self.set_active_formatter_stylesheet_in_prefs(filename)
        
            
    def on_formatters_combo_changed(self, combo):
        '''
        '''        
        self.refresh_active_formatter_options()
        self.renderers_combo.set_sensitive(True)
        self.stylesheet_button.set_sensitive(True)        
        if combo.get_active() == -1:
            self.remove_button.set_sensitive(False)
        else:
            self.remove_button.set_sensitive(True)
    
            
    def add_formatter(self, name, renderer=None, stylesheet=None):        
        '''
        add a formatter with name to formatter in the prefs, the renderer and
        stylesheet both default to None
        '''
        formatters = prefs[formatters_list_pref]
        if formatters is None:
            formatters = {}
        if name in formatters:
            utils.message_dialog('a formatter with this name already exists')
        else:
            formatters[name] = {'renderer': renderer, 
                                'stylesheet': stylesheet}
        prefs[formatters_list_pref] = formatters
        model = self.formatters_combo.get_model()
        it = model.append([name])
        self.formatters_combo.set_active_iter(it)
        
    
    def get_active_formatter(self):
        '''
        get the formatter prefs for the active formatter
        '''
        name = get_active_formatter_name(self)
        return prefs[formatters_list_pref][name]


    def get_active_formatter_name(self):
        '''
        get the name of the current formatter
        '''
        return self.formatters_combo.get_active_text()
    
    
    def set_active_formatter_renderer_in_prefs(self, renderer):
        '''
        set the renderer of the currently selected formatter
        '''
        name = self.get_active_formatter_name()
        self.set_formatter_renderer_in_prefs(name, renderer)
    
    
    def set_active_formatter_stylesheet_in_prefs(self, stylesheet):
        '''
        set the stylesheet of the currently selected formatter
        '''
        name = self.get_active_formatter_name()
        self.set_formatter_stylesheet_in_prefs(name, stylesheet)
    
    
    def set_formatter_renderer_in_prefs(self, name, renderer):
        '''
        set the renderer for the formatter by name
        '''
        formatters = prefs[formatters_list_pref]
        if name not in formatters:
            raise ValueError('could not get formatter from the prefs called %s'
                             % name)
        formatters[name]['renderer'] = renderer
        prefs[formatters_list_pref] = formatters
    
    
    def set_formatter_stylesheet_in_prefs(self, name, stylesheet):
        '''
        set the renderer for the formatter by name
        '''
        formatters = prefs[formatters_list_pref]
        if name not in formatters:
            raise ValueError('could not get formatter from the prefs called'% \
                             name)
        formatters[name]['stylesheet'] = stylesheet        
        prefs[formatters_list_pref] = formatters
        
        
    def set_formatter_options_in_prefs(self, name, renderer, stylesheet):
        '''
        set both the renderer and stylesheet on formatter by name
        '''
        set_formatter_renderer_in_prefs(name, renderer)
        set_formatter_stylesheet_in_prefs(name, stylesheet)
        
        
    def refresh_active_formatter_options(self):
        '''
        change the status of the options widgets according to the active 
        formatter
        '''
        name = self.get_active_formatter_name()
        if name is None:
            self.renderers_combo.set_active(-1)
            self.renderers_combo.set_sensitive(False)
            self.stylesheet_button.set_filename('')
            self.stylesheet_button.set_sensitive(False)
            return

        #debug(name)
        try:        
            formatter = prefs[formatters_list_pref][name]
        except:
            return
        
        renderer = formatter['renderer']        
        if formatter['renderer'] is not None:
            try:            
                combo_set_active_text(self.renderers_combo, formatter['renderer'])
            except:
                pass
        else:
            self.renderers_combo.set_active(-1)
        
        stylesheet = formatter['stylesheet']
        if stylesheet is None:
            stylesheet = ''        
        self.stylesheet_button.set_filename(stylesheet)
        
        
    @staticmethod
    def in_model(model, item):  
        '''
        '''        
        if model == None:
            return False      
        for i in model:
            if item == i:
                return True
        return False
        

class FormatterTool(BaubleTool):    
    label = "Formatter"
    
    @classmethod
    def start(self):        
        '''
        '''    
        # get all of the current plants from the view
        import bauble
        view = bauble.app.gui.get_current_view()        

#        if not isinstance(view, bauble.plugins.searchview.search.SearchView):
#            raise Error('Formmatter: can only format results from the '\
#                        'search vew')
                        
        # TODO: this assumes a bit too much about SearchView's internal workings
        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog("Search for something first.")
            return
        
        all_plants = {}
        def add_plants(plants):
            for p in plants:
                id = str(p.id)
                if id not in all_plants.keys():
                    all_plants[id] = p               
                         
        def get_plants_from_accessions(accessions):
            p = []
            for acc in accessions:
                p += acc.plants
            return p
        
        bauble.app.set_busy(True)
        # extract the plants from the search results
        for row in model:
            value = row[0]
            if isinstance(value, tables["Family"]):
                for gen in value.genera:
                    for sp in gen.species:
                        p = get_plants_from_accessions(sp.accessions)
                        add_plants(p)
            elif isinstance(value, tables["Genus"]):
                for sp in value.species:
                    p = get_plants_from_accessions(sp.accessions)
                    add_plants(p)
            elif isinstance(value, tables["Species"]):
                p = get_plants_from_accessions(value.accessions)
                add_plants(p)
            elif isinstance(value, tables["Accession"]):
                add_plants(value.plants)
            elif isinstance(value, tables["Plant"]):
                add_plants([value])
            elif isinstance(value, tables["Location"]):
                add_plants(value.plants)
            
        if len(all_plants) == 0:
            utils.message_dialog('There are no plants in the search '\
                                 'results. Please try another search.')
            bauble.app.set_busy(False)
            return
        
        formatter = Formatter()    
        try:            
            pdf_filename = formatter.start(all_plants.values())
        except:
            msg = 'Could not create PDF file.'
            utils.message_details_dialog(msg, traceback.format_exc(), 
                                         gtk.MESSAGE_ERROR)
        else:
            if pdf_filename is not None:            
                utils.startfile(pdf_filename)
        bauble.app.set_busy(False)       
    
    
    
class FormatterPlugin(BaublePlugin):
    '''
    '''    
    tools = [FormatterTool]
    depends = ["ABCDImexPlugin"]
        
    try:
        import libxml2
    except ImportError: 
        FormatterTool.enabled = False
        debug(traceback.format_exc())
    
    try:
        import libxslt
    except ImportError:
        FormatterTool.enabled = False
        debug(traceback.format_exc())

plugin = FormatterPlugin        
    
