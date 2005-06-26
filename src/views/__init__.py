#
# view module
#

# TODO: on first start no view will be visible unless a default is selected

import os, os.path
import re
import gtk
import gobject


# here the Frame is just being used as a container,
# this will cause some double framing when the view is placed in the gui
# but it's easier than subclassing gtk.Bin and implementing 
# size_allocate/size_request, plus we don't usually have more than one or two
# views open at a time
class View(gtk.Frame):
    """
    all Bauble views should be a subclass of this class
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
    modules = {}
    def __init__(self):
        modules = []
        path, name = os.path.split(__file__)
        if path.find("library.zip") != -1: # using py2exe
            pkg = "views"
            zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
            x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
            s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
            rx = re.compile(s.encode('string_escape'))
            for filename in x:
                m = rx.match(filename)
                if m is not None:
                    modules.append('%s.%s' % (pkg, m.group(1)))
        else:                
            for d in os.listdir(path):
                full = path + os.sep + d                
                if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                    modules.append("views." + d)

        for m in modules:
            print "importing " + m
            mod = __import__(m, globals(), locals(), ['views'])
            if hasattr(mod, "view"): 
                self[mod.label] = mod.view
                self.modules[mod.view] = m
                
    
    def __getattr__(self, attr):
        if not self.has_key(attr):
            return None
        return self[attr]

views = _views()    


        
