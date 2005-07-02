#
# this is just a dummy file so i can import on this directory
#

import imp, os, sys

def main_is_frozen():
   return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze
           
import pygtk
if not main_is_frozen():
    pygtk.require("2.0")
import gtk
import re


def plantname2str(p, authors=False):    
    #TODO: this needs alot of work to be complete
    name = str(p.genus) + " " + p.sp
    if p.isp_rank is not None:
        name += " %s" % p.isp_rank
    if p.isp is not None:
        name += " %s" % p.isp
    return name


def get_combo_text(combo, column=0):
    model = combo.get_model()
    active = combo.get_active()
    if active < 0:
        return None
    return model[active][column]    


def message_dialog(msg, type=gtk.MESSAGE_INFO):
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=type,
                          buttons=gtk.BUTTONS_OK,
                          message_format=msg)        
    r = d.run()
    d.destroy()
    

def yes_no_dialog(msg):
    d = gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          type=gtk.MESSAGE_QUESTION,
                          buttons = gtk.BUTTONS_YES_NO,
                          message_format=msg)        
    r = d.run()
    d.destroy()
    return r == gtk.RESPONSE_YES


def get_main_dir():
   if main_is_frozen():
       dir = os.path.dirname(sys.executable)
   else: dir = os.path.dirname(sys.argv[0])
   if dir == "": 
       dir = os.curdir
   return dir
   
   
   