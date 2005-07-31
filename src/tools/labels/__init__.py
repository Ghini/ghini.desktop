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

import os
import gtk
from tables import tables

class LabelMaker(gtk.Dialog):
    def __init__(self, plants, title='Label Maker', parent=None):
        """
        plants - the list of Plants to generate the labels from
        """
        gtk.Dialog.__init__(self, title, parent,
                            flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, 
                            buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        self.plants = plants
        self.create_gui()            
        #self.connect('on-)
        
        
    def create_gui(self):
        
        model = gtk.ListStore(str, str)
        for p in self.plants:
            id = str(p.accession.acc_id) + '.' + str(p.plant_id)
            name = p.accession.plantname
            model.append([id, name])
                        
        plants_view = gtk.TreeView(model)
        
        # create the checkbox column
        # create the id column
        r = gtk.CellRendererText()
        c = gtk.TreeViewColumn("Id", r, text=0)
        plants_view.append_column(c)
        # create the name column
        r = gtk.CellRendererText()
        c = gtk.TreeViewColumn("Name", r, text=1)
        plants_view.append_column(c)
                
        self.vbox.pack_start(plants_view)
        self.show_all()
        #dialog.vbox.show_all()
        
    
    def create_pdf(self, filename=None):
        import tempfile
        if filename is None:
            # create a temporary file            
            file, filename = tempfile.mkstemp()
            #file.close()
        
        print 'create_pdf: ' + filename    
        from tools.import_export.abcd import ABCDExporter
        dummy, abcd_filename = tempfile.mkstemp()
        exporter = ABCDExporter()
        exporter.run(abcd_filename)
        
        dummy, fo_filename = tempfile.mkstemp()
        xslt_filename  = '/home/brett/devel/bauble/src/tools/labels/label.xsl'
        # run the command
        xslt_cmd = 'xsltproc %s %s > %s' % (xslt_filename, abcd_filename, fo_filename)
        print xslt_cmd
        os.system(xslt_cmd)
        
        fo_cmd = 'xep -fo %s -pdf %s' % (fo_filename, filename)
        print fo_cmd
        os.system(fo_cmd)
        
        #cmd = "xsltproc label.xsl %s | xep -fo - -pdf %s" % (abcd_filename, filename)
        #print cmd
        #os.system(cmd)
            
        # open and return the file hander or filename so we don't have to close it
        return filename
        
    