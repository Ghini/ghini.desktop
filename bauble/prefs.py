#
# prefs.py
#

import sys, os
import gtk
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.paths as paths
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug, warning

# TODO: include the version of the database in the prefs so that if the prefs
# are opened with a different version then the user will know and possible
# migrate pref version though i don't think the prefs  format will change much

# TODO: make sure the version numbers are compatible,
# if we are upgrading to a new version we should copy the old
# config somewhere else, copy any relevant keys and set the config
# version in the new file

# TODO: should also possibly check that the config version and
# database versions match up

# TODO: maybe we should have a create method that creates the preferences
# todo a one time thing if the files doesn't exist

default_filename = 'config'
default_prefs_file = os.path.join(paths.user_dir(), default_filename)

prefs_icon_dir = os.path.join(paths.lib_dir(), 'images')
general_prefs_icon = os.path.join(prefs_icon_dir, 'prefs_general.png')
security_prefs_icon = os.path.join(prefs_icon_dir, 'prefs_security.png')

config_version_pref = 'bauble.config.version'
config_version = bauble.version[0], bauble.version[1]

## class PreferencesMgr(gtk.Dialog):

##     def __init__(self):
##         gtk.Dialog.__init__(self, "Preferences", None,
##                    gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
##                    (gtk.STOCK_OK, gtk.RESPONSE_OK,
##                     gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
##         self.current_frame = None
##         self.create_gui()


##     def create_gui(self):
##         model = gtk.ListStore(str, gtk.gdk.Pixbuf)

##         #pixbuf = gtk.gdk.pixbuf_new_from_file("images/prefs_general.png")
##         pixbuf = gtk.gdk.pixbuf_new_from_file(general_prefs_icon)
##         model.append(["General", pixbuf])

##         #pixbuf = gtk.gdk.pixbuf_new_from_file("images/prefs_security.png")
##         pixbuf = gtk.gdk.pixbuf_new_from_file(security_prefs_icon)
##         model.append(["Security", pixbuf])

##         self.icon_view = gtk.IconView(model)
##         self.icon_view.set_text_column(0)
##         self.icon_view.set_pixbuf_column(1)
##         self.icon_view.set_orientation(gtk.ORIENTATION_VERTICAL)
##         self.icon_view.set_selection_mode(gtk.SELECTION_SINGLE)
##         self.icon_view.connect("selection-changed", self.on_select, model)
##         self.icon_view.set_columns(1) # this isn't in the pygtk docs
##         self.icon_view.set_item_width(-1)
##         self.icon_view.set_size_request(72, -1)

##         self.content_box = gtk.HBox(False)
##         self.content_box.pack_start(self.icon_view, fill=True, expand=False)
##         self.icon_view.select_path((0,)) # select a category, will create frame
##         self.show_all()
##         self.vbox.pack_start(self.content_box)
##         self.resize(640, 480)
##         self.show_all()


##     def on_select(self, icon_view, model=None):
##         selected = icon_view.get_selected_items()
##         if len(selected) == 0: return
##         i = selected[0][0]
##         category = model[i][0]
##         if self.current_frame is not None:
##             self.content_box.remove(self.current_frame)
##             self.current_frame.destroy()
##             self.current_frame = None
##         if category == "General":
##             self.current_frame = self.create_general_frame()
##         elif category == "Security":
##             self.current_frame = self.create_security_frame()
##         self.content_box.pack_end(self.current_frame, fill=True, expand=True)
##         self.show_all()


##     def create_general_frame(self):
##         frame = gtk.Frame("General")
##         box = gtk.VBox(False)
##         box.pack_start(gtk.Label("Nothing to see here. Move on."))
##         frame.add(box)
##         return frame


##     def create_security_frame(self):
##         frame = gtk.Frame("Security")
##         box = gtk.VBox(False)
##         box.pack_start(gtk.Label("Nothing to see here. Move on."))
##         frame.add(box)
##         return frame


from ConfigParser import RawConfigParser

class _prefs(dict):

    def __init__(self, filename=default_prefs_file):
        self._filename = filename


    def init(self):
        '''
        initialize the preferences, should only be called from app.main
        '''
        # create directory tree of filename if it doesn't yet exist
        head, tail = os.path.split(self._filename)
        if not os.path.exists(head):
            os.makedirs(head)

        self.config = RawConfigParser()

        # set the version if the file doesn't exist
        if not os.path.exists(self._filename):
            self[config_version_pref] = config_version
        else:
            self.config.read(self._filename)
        version = self[config_version_pref]
        if version is None:
            warning('%s has no config version pref' % self._filename)
            warning('setting the config version to %s.%s' % (config_version))
	    self[config_version_pref] = config_version


    @staticmethod
    def _parse_key(name):
        index = name.rfind(".")
        return name[:index], name[index+1:]


    def get(self, key, default):
        '''
        get value for key else return default
        '''
        value = self[key]
        if value is None:
            return default
        return value


    def __getitem__(self, key):
        section, option = _prefs._parse_key(key)
        # this doesn't allow None values for preferences
        if not self.config.has_section(section) or \
           not self.config.has_option(section, option):
            return None
        else:
            i = self.config.get(section, option)
            eval_chars = '{[('
            if i[0] in eval_chars: # then the value is a dict, list or tuple
                return eval(i)
            elif i == 'True' or i == 'False':
                return eval(i)
            return i
            #return self.config.get(section, option)


    def iteritems(self):
        return [('%s.%s' % (section, name), value) for section in sorted(prefs.config.sections()) for name, value in prefs.config.items(section)]


    def __setitem__(self, key, value):
        section, option = _prefs._parse_key(key)
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))


    def __contains__(self, key):
        section, option = _prefs._parse_key(key)
        if self.config.has_section(section) and \
           self.config.has_option(section, option):
            return True
        return False


    def save(self):
        print self.config.items('conn')
        try:
            f = open(self._filename, "w+")
            self.config.write(f)
            f.close()
        except:
            msg = _("Bauble can't save your user preferences. \n\nPlease "
                    "check the file permissions of your config file:\n %s" \
                    % self._filename)
            if bauble.gui is not None and bauble.gui.window is not None:
                utils.message_dialog(msg, type=gtk.MESSAGE_ERROR,
                                     parent=bauble.gui.window)


# TODO: remember pane sizes

class PrefsView(pluginmgr.View):
    """
    The PrefsView displays the values of in the preferences and the registry.
    """

    pane_size_pref = 'bauble.prefs.pane_position'

    def __init__(self):
        super(PrefsView, self).__init__()
        self.create_gui()

#     def create_registry_view(self):
#         pass

    def create_meta_view(self):
        pass

    def create_gui(self):
        pane = gtk.VPaned()
        self.pack_start(pane)
        pane.set_border_width(5)
        width, height = pane.size_request()


        # TODO: check-resize and move_handle are not the correct
        # signals when the pane is resized....so right now the size is
        # not getting saved in the prefs
        def on_move_handle(paned, data=None):
            print p.get_position()
            prefs[self.pane_size_pref] = p.get_position()
        pane.connect('check-resize', on_move_handle)

        if prefs.get(self.pane_size_pref, None) is not None:
            pane.set_position(prefs[self.pane_size_pref])
        else:
            # setting the default to half the height of the window is
            # close enough to the middle even though the top pane will
            # be a little larger
            rect = bauble.gui.window.get_allocation()
            pane.set_position(int(rect.height/2))

        label = gtk.Label()
        label.set_markup(_('<b>Preferences</b>'))
        label.set_padding(5, 0)
        frame = gtk.Frame()
        frame.set_label_widget(label)
        view = self.create_prefs_view()
        frame.add(view)
        pane.pack1(frame)

        label = gtk.Label()
        label.set_markup(_('<b>Registry</b>'))
        label.set_padding(5, 0)
        frame = gtk.Frame()
        frame.set_label_widget(label)
        view = self.create_registry_view()
        frame.add(view)
        pane.pack2(frame)


    def create_tree(self, columns, itemsiter):
        treeview = gtk.TreeView()
        treeview.set_rules_hint(True)

        i = 0
        model_cols = []
        for c in columns:
            renderer = gtk.CellRendererText()
            column = gtk.TreeViewColumn(c, renderer, text=i)
            treeview.append_column(column)
            i += 1
            model_cols.append(str)

        model = gtk.ListStore(*model_cols)
        for i in itemsiter:
            model.append(i)
        treeview.set_model(model)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(treeview)
        return sw


    def create_prefs_view(self):
        global prefs
        tree = self.create_tree([_('Names'), _('Values')], prefs.iteritems())
        return tree

    def create_registry_view(self):
        from bauble.pluginmgr import Registry
        tree = self.create_tree([_('Names'), _('Values')],
                                Registry().iteritems())
        return tree




class PrefsCommandHandler(pluginmgr.CommandHandler):

    command = ('prefs', 'config')
    view = None

    def __call__(self, arg):
        pass


    def get_view(self):
        if self.view is None:
            self.view = PrefsView()
            return self.view



pluginmgr.register_command(PrefsCommandHandler)

prefs = _prefs()


