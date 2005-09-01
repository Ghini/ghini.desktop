#
# prefs.py
#

import sys, os
import gtk
import bauble.utils as utils
import bauble.paths as paths
from bauble.utils.log import debug

# TODO: i think it would be a hell of alot simpler and easier to
# read if we just stuck with a
# name = value format and remove all that ugly set_pref crap

if sys.platform == "win32":
    if os.environ.has_key("APPDATA"):
        default_prefs_file = os.environ["APPDATA"] + os.sep + "Bauble" + os.sep + "user.py"
    else:
        raise Exception("Could not path to store preferences")
elif sys.platform == "linux2":
    if os.environ.has_key("HOME"):
        default_prefs_file = os.environ["HOME"] + os.sep + ".bauble" + os.sep + "user.py"
    else:
        raise Exception("Could not path to store preferences")
else:
    raise Exception("Could not path to store preferences: unsupported platform")

prefs_icon_dir = paths.lib_dir() + os.sep + "images" + os.sep
general_prefs_icon = prefs_icon_dir + "prefs_general.png"
security_prefs_icon = prefs_icon_dir + "prefs_security.png"


class PreferencesMgr(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self, "Preferences", None,
                   gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                   (gtk.STOCK_OK, gtk.RESPONSE_OK,
                    gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        self.current_frame = None
        self.create_gui()


    def create_gui(self):
        model = gtk.ListStore(str, gtk.gdk.Pixbuf)
        
        #pixbuf = gtk.gdk.pixbuf_new_from_file("images/prefs_general.png")
        pixbuf = gtk.gdk.pixbuf_new_from_file(general_prefs_icon)
        model.append(["General", pixbuf])
        
        #pixbuf = gtk.gdk.pixbuf_new_from_file("images/prefs_security.png")
        pixbuf = gtk.gdk.pixbuf_new_from_file(security_prefs_icon)
        model.append(["Security", pixbuf])
        
        self.icon_view = gtk.IconView(model)
        self.icon_view.set_text_column(0)
        self.icon_view.set_pixbuf_column(1)
        self.icon_view.set_orientation(gtk.ORIENTATION_VERTICAL)
        self.icon_view.set_selection_mode(gtk.SELECTION_SINGLE)
        self.icon_view.connect("selection-changed", self.on_select, model)
        self.icon_view.set_columns(1) # this isn't in the pygtk docs
        self.icon_view.set_item_width(-1)
        self.icon_view.set_size_request(72, -1)
        
        self.content_box = gtk.HBox(False)
        self.content_box.pack_start(self.icon_view, fill=True, expand=False)
        self.icon_view.select_path((0,)) # select a category, will create frame
        self.show_all()
        self.vbox.pack_start(self.content_box)        
        self.resize(640, 480)
        self.show_all()


    def on_select(self, icon_view, model=None):
        selected = icon_view.get_selected_items()
        if len(selected) == 0: return
        i = selected[0][0]
        category = model[i][0]
        if self.current_frame is not None:
            self.content_box.remove(self.current_frame)
            self.current_frame.destroy()
            self.current_frame = None
        if category == "General":
            self.current_frame = self.create_general_frame()
        elif category == "Security":
            self.current_frame = self.create_security_frame()    
        self.content_box.pack_end(self.current_frame, fill=True, expand=True)
        self.show_all()
        
        
    def create_general_frame(self):
        frame = gtk.Frame("General")
        box = gtk.VBox(False)
        box.pack_start(gtk.Label("Nothing to see here. Move on."))
        frame.add(box)
        return frame        


    def create_security_frame(self):
        frame = gtk.Frame("Security")        
        box = gtk.VBox(False)
        box.pack_start(gtk.Label("Nothing to see here. Move on."))
        frame.add(box)
        return frame        


#from ConfigParser import ConfigParser
#
#class _prefs(dict):
#    
#    # preference keys
#    conn_default_pref = "conn.default"
#    conn_list_pref = "conn.list"
#    
#    def __init__(self, filename):
#        config = ConfigParser()
#        config.read(filename)
#
#    @staticmethod
#    def _parse_key(name):
#        index = name.rfind(".")
#        return name[:index], name[index+1:]
#
#
#    def __getitem__(self, item):
#        section, option = _prefs._parse_key(item)
#        return config.get(section, option)
#
#        
#    def __setitem__(self, item, value):
#        section, option = _prefs._parse_key(item)
#        config.set(section, option, value)
#
#        
#    def __contains__(self, item):
#        section, option = _prefs._parse_key(item)
#        return False
#
#
#    def __del__(self, item):
#        """
#        """
#        section, option = _prefs._parse_key(item)
#        #if has section: remove option
#        # if n_option in section == -
#        #     remove section
#        
#        pass


# TODO: should just make this a static class named prefs though i don't know
# though i don't know how well this would work access the dict superclass of
# the class, have a dict in the module and module level functions to manipulate
# it like we do in plugins
class _prefs(dict):
    """
    handles the loading, storing, getting and settings of preferences
    uses the Borg design patter so that all instances share the same data
    NOTE: if you expect a list with one item then the list should be written
    like (item,) witha trailing comma or it will get interpreted as string
    """
    
    # preference keys
    conn_default_pref = "conn.default"
    conn_list_pref = "conn.list"

    _loaded = False
    _filename = default_prefs_file    
    
    def __init__(self):
        if not os.path.exists(self._filename):
            path, file = os.path.split(self._filename)
            if not os.path.exists(path):
                os.mkdir(path)
            f = open(self._filename, "w") # touch
            f.close() 
        

    def load(self, filename=_filename):
        debug("entered prefs.load")
        self._loaded=True
        # TODO: if this is loaded after  the user has set some preferences
        # then those preferences could be overwritten, need to set some
        # sort of flag to not overwrite preferences
        # it's a bit early to set this but set_pref won't work otherwise
        try:
            execfile(filename)        
        except: 
            msg = "Could not load preferences file: " + filename
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            raise
        else:
            self._loaded=True


    def save(self, filename=_filename):
        # TODO: open and backup old file in case something goes wrong
        # then we can restore the preferences instead of losing them
        f = open(filename, "w") # open, truncate
        template = 'set_pref("%s", %s)\n'
        for key in sorted(self.keys()):
            value = self[key]
            if type(value) == str: 
                value = '"%s"' % value
            p = template % (key, value)
            f.write(p)
    

    def __getitem__(self, key):
        if not self._loaded:
            raise Exception("Preference not loaded")
        if not self.has_key(key): 
            return None
        return dict.__getitem__(self, key)
        
        
    def __setitem__(self, key, value):
        if not self._loaded:
            raise Exception("Preference not loaded")
        else:
            dict.__setitem__(self, key, value)
            

prefs = _prefs()

# should only be used by the preferences file
def set_pref(key, value):
    prefs[key] = value

prefs.load()

