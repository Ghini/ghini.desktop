#
# view module
#

# TODO: on first start no view will be visible unless a default is selected

import os, os.path

import pygtk
pygtk.require("2.0")
import gtk
import gobject


# here the Frame is just being used as a container,
# this will cause some double framing when the view is placed in the gui
# but it's easier than subclassing gtk.Bin and implementing 
# size_allocate/size_request, plus we don't usually have more than one or two
# views open at a time
class View(gtk.Frame):
    """
    all Bauble views should be a subclass of this
    """
    def __init__(self):
        gtk.Frame.__init__(self)
        self.set_shadow_type(gtk.SHADOW_NONE)

class _views(dict):
    """
    a dictionary of all the registered views
    this is populated dynamically by search for all modules in the 
    this subdirectory
    """
    def __init__(self):
        path, name = os.path.split(__file__)
        for d in os.listdir(path):
            full = path + os.sep + d 
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                m = __import__("views." + d, globals(), locals(), ['views'])
                if hasattr(m, "view"): # in case the module doesn't provide a view
                    self[m.view.__name__] = m.view
                
        
    def __getattr__(self, attr):
        if not self.has_key(attr):
            return None
        return self[attr]

views = _views()    


        
