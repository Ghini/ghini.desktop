#
# this is just a dummy file so i can import on this directory
#

import pygtk
pygtk.require("2.0")
import gtk
import re

rx = re.compile(" {2,}")
def plantname2str(plantname, authors=False):    
    # should return the fully qualified name based on the plantname
    # row, there probably a more efficient way
    p = "%s %s %s %s" % (plantname.genus, plantname.sp, plantname.isp_rank,
                      plantname.isp)
    # replace two or more space with one space    
    p2 =  rx.sub(" ", p)    
    p2 = p2.strip()
    return p2


def get_combo_text(combo, column=0):
    model = combo.get_model()
    active = combo.get_active()
    if active < 0:
        return None
    return model[active][column]    


def are_you_sure(msg):
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_QUESTION,
                          buttons = gtk.BUTTONS_YES_NO,
                          message_format=msg)        
    r = d.run()
    d.destroy()
    return r == gtk.RESPONSE_YES


class ProgressDialog(gtk.Dialog):
    def __init__(self, title=""):
        gtk.Dialog.__init__(self, title, None, gtk.DIALOG_NO_SEPARATOR,
#                            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                            (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
    
        self.create_gui()

    def create_gui(self):
        self.pb = gtk.ProgressBar()
        self.vbox.pack_start(self.pb)
        

    def run(self):
        self.show_all()
        gtk.Dialog.run(self)        
        #while True:
        #self.pb.pulse()
        
    
    def pulse(self):
        self.pb.pulse()