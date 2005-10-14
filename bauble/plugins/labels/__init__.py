#
# label maker modules
#
# NOTE: this module depends on the XEP xsl formatter from RenderX (renderx.com)
# which is a commercial product, i haven't yet found a free/open alternative
# that can implment enough of the XSL-FO standard that we need to generate the
# labels, if anyone else know how we can change the XSL output to work with 
# Apache's FOP then that would be ideal
# 
# The other part that sucks is that this all requires Java, it would be ideal
# if xmlroff supported more of the XSL standard

# TODO: once the label layout is formalized then we can put the xsl stylesheet
# inside this module as a multiline string to avoid having to find the file on 
# the disk

# ********
# TODO: this tool should be included in the search view plugin or at least
# be a separate plugin that requires search view 
#***********

import os, traceback
import gtk
import bauble.utils as utils
from bauble.plugins import BaublePlugin, BaubleTool, plugins, tables
from bauble.utils.log import log, debug
from bauble.plugins.imex_abcd import abcd
    
class LabelMaker(gtk.Dialog):
        
    def __init__(self, plants, title='Label Maker', parent=None):
        """
        plants - the list of Plants to generate the labels from
        """
        gtk.Dialog.__init__(self, title, parent,
                            flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, 
                            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        self.create_gui(plants)
        
        
    def check_cell_data_func(self, column, cell, model, iter, data=None):
        yes_no = model.get_value(iter, 0)
        cell.set_property('active', yes_no)        
        
        
    def id_cell_data_func(self, column, cell, model, iter, data=None):
        plant = model.get_value(iter, 1)
        id = str(plant.accession.acc_id) + '.' + str(plant.plant_id)        
        cell.set_property('text', id)
    
    
    def name_cell_data_func(self, column, cell, model, iter, data=None):
        plant = model.get_value(iter, 1)
        cell.set_property('text', plant.accession.plantname)        
        
        
    def on_renderer_toggled(self, widget, path, data=None):
        active = widget.get_active()
        model = self.plants_view.get_model()
        it = model.get_iter(path)
        model.set_value(it, 0, not active)

        
    def create_gui(self, plants):
        
        model = gtk.ListStore(bool, object)
        for p in plants:
            model.append([True, p])
                        
        self.plants_view = gtk.TreeView(model)
        
        # create the checkbox column
        r = gtk.CellRendererToggle()        
        r.connect("toggled", self.on_renderer_toggled)
        c = gtk.TreeViewColumn("", r)
        c.set_cell_data_func(r, self.check_cell_data_func)
        self.plants_view.append_column(c)
        
        # create the id column
        r = gtk.CellRendererText()
        c = gtk.TreeViewColumn("Id", r)
        c.set_cell_data_func(r, self.id_cell_data_func)
        self.plants_view.append_column(c)
        
        # create the name column
        r = gtk.CellRendererText()
        c = gtk.TreeViewColumn("Name", r)
        c.set_cell_data_func(r, self.name_cell_data_func)
        self.plants_view.append_column(c)
                
        self.vbox.pack_start(self.plants_view)
        self.show_all()
        
        
    def create_pdf(self, filename=None):
        import libxml2
        import libxslt
        import tempfile
        if filename is None:
            # no filename, create a temporary file            
            dummy, filename = tempfile.mkstemp()                
        
        # get all the plants from the model in ABCD format
        plants = []
        for yes_no, plant in self.plants_view.get_model():
            if yes_no:
                plants.append(plant)
        abcd_data = abcd.plants_to_abcd(plants)
        
                
        # create xsl fo file
        dummy, fo_filename = tempfile.mkstemp()
        xslt_filename = os.path.dirname(__file__) + os.sep + 'label.xsl'
#        debug(xslt_filename)
        # how come we don't have to free style_doc???
        style_doc = libxml2.parseFile(xslt_filename) 
        style = libxslt.parseStylesheetDoc(style_doc)
        doc = libxml2.parseDoc(abcd_data)
        result = style.applyStylesheet(doc, None)
        style.saveResultToFilename(fo_filename, result, 0)
        style.freeStylesheet()
        doc.freeDoc()
        result.freeDoc()
        
        # run the formatter to produce the pdf file, xep has to be on the
        # path
        fo_cmd = 'xep -fo %s -pdf %s' % (fo_filename, filename)
#        debug(fo_cmd)
        os.system(fo_cmd)    
            
        # open and return the file hander or filename so we don't have to close it
        return filename    
    
    
    def create_pdf_old(self, filename=None):
        # TODO: should change this to use libxslt then we can return the abcd
        # file from the exporter, pass that directly to libxslt and then
        # the only os.system call we have to make is to XEP
     
        import tempfile
        if filename is None:
            # create a temporary file            
            dummy, filename = tempfile.mkstemp()
        
        from tools.import_export.abcd import ABCDExporter
        dummy, abcd_filename = tempfile.mkstemp()
        exporter = ABCDExporter()
        
        # get all the plants from the model
        plants = []
        for yes_no, plant in self.plants_view.get_model():
            if yes_no:
                plants.append(plant)
        exporter.run(abcd_filename, plants)
        
        dummy, fo_filename = tempfile.mkstemp()
        xslt_filename = os.path.dirname(__file__) + os.sep + 'label.xsl'
        # run the xslt command to create the fo file
        xslt_cmd = 'xsltproc %s %s > %s' % (xslt_filename, abcd_filename, fo_filename)
        print xslt_cmd
        os.system(xslt_cmd)
        
        # run the formatter to produce the pdf file
        fo_cmd = 'xep -fo %s -pdf %s' % (fo_filename, filename)
        print fo_cmd
        os.system(fo_cmd)    
            
        # open and return the file hander or filename so we don't have to close it
        return filename

#
# the plugin
#

class LabelMakerTool(BaubleTool):    
    label = "Label Maker"
    
    @classmethod
    def start(self):
        #import tools.labels
        
        # TODO: really the Label Maker tool should only be sensitive if the 
        # search view is visible but right now since we only have one view 
        # we won't worry about that
        
        # get all of the current plants from the view
        import bauble
        view = bauble.app.gui.get_current_view()        
        #view = self.get_current_view()
        #if not isinstance(view, views.Search):
        #if not instance(view, bauble.plugins.searchview.search.SearchView):
        
        # TODO: change plugins.views so we can access it like this
        # if not isinstance(view, plugins.views["SearchView"]):
        if not isinstance(view, bauble.plugins.searchview.search.SearchView):
            raise Error("GUI.on_tools_menu_label_maker: can only "\
                        "make labels from the search vew")
                        
        # TODO: this assumes a but too much about SearchView's internal workings
        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog("Search for something first.")
            return
        
        plants = []
        for row in model:
            value = row[0]
            # right now we don't create labels for all plants under
            # families and genera
            #tables = plugins.tables
            if isinstance(value, tables["Family"]):
                print "family: " + str(value)
            elif isinstance(value, tables["Genus"]):
                print "genera: " + str(value)
            elif isinstance(value, tables["Plantname"]):
                for acc in value.accessions:
                    plants += acc.plants
            elif isinstance(value, tables["Accession"]):
                plants += value.plants
            elif isinstance(value, tables["Plant"]):
                plants.append(value)            
            elif isinstance(value, tables["Location"]):
                plants += value.plants
            
        #print plants
        label_maker = LabelMaker(plants)
        response = label_maker.run()
        if response == gtk.RESPONSE_ACCEPT:
            pdf_filename = label_maker.create_pdf()
            print pdf_filename
            utils.startfile(pdf_filename)        
        label_maker.destroy()
    
    
class LabelMakerPlugin(BaublePlugin):
    tools = [LabelMakerTool]
    depends = ["ABCDImexPlugin"]
        
    try:
        import libxml2
    except ImportError: 
        LabelMakerTool.enabled = False
        debug(traceback.format_exc())
    
    try:
        import libxslt
    except ImportError:
        LabelMakerTool.enabled = False
        debug(traceback.format_exc())

plugin = LabelMakerPlugin
        
    