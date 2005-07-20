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
    return name.strip()


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


def dms_to_decimal(dir, deg, min, sec):
    """
    convert degrees, minutes, seconds to decimal
    """
    # TODO: more test cases
    dec = (((sec/60.0) + min) /60.0) + deg
    if dir == 'W' or dir == 'S':
        dec = -dec
    return dec
    
        
def decimal_to_dms(decimal, long_or_lat):
    """
    long_or_lat: should be either 'long' or 'lat'
    """
    # NOTE: if speed is an issue, which i don't think it ever will be
    # this could probably be optimized
    # TODO: more test cases
    dir_map = { 'long': ['E', 'W'],
                'lat':  ['N', 'S']}
    dir = dir_map[long_or_lat][1]
    if decimal < 0:
        dir = dir_map[long_or_lat][0]
        
    dec = abs(decimal)
    d = abs(int(dec))
    m = abs((dec-d)*60)
    s = abs((int(m)-m) * 60)
    return dir, int(d), int(m), int(s)
    
    
def longitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'long')

    
def latitude_to_dms(decimal):
    return decimal_to_dms(decimal, 'lat')
   
    
if __name__ == '__main__':
    """
    could probably put this in a doctest
    """
    dec = dms_to_decimal('W', 87, 43, 41)
    dir, deg, min, sec = decimal_to_dms(dec, 'long')
    print dec
    print '%s %d %d %d' % (dir, deg, min, sec)
   
   