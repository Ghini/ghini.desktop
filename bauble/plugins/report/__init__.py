#
# __init__.py
#
# Description : report plugin
#

import os, sys, traceback, re
import gobject, gtk
from sqlalchemy import *
import lxml.etree as etree
import lxml._elementpath # put this here sp py2exe picks it up
import bauble
from bauble.i18n import *
import bauble.utils as utils
import bauble.paths as paths
from bauble.prefs import prefs
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import log, debug

# BUGS:
# https://bugs.launchpad.net/bauble/+bug/146998 - Don't hardcode how to get the plants in report plugin


# name: formatter_class, formatter_kwargs
config_list_pref = 'report.configs'

# the default report generator to select on start
default_config_pref = 'report.default'
formatter_settings_expanded_pref = 'report.settings.expanded'


def get_all_plants(objs, acc_status=None, session=None):
    """
    @param objs: a list of object to search through for Plant instances
    @param acc_status: only return thost plants whose acc_status matches
    @param session: the session that the returned plants should be attached to
    """
    if acc_status is None:
        acc_status = 'Living accession', None

    if session is None:
        session = bauble.Session()

    from bauble.plugins.garden.plant import Plant, plant_table
    all_plants = {}

    plant_query = session.query(Plant)

    def add_plants(plants):
        for p in plants:
            if p.id not in all_plants and p.acc_status in acc_status:
                all_plants[p.id] = p


    def add_plants_from_accessions(accessions):
        '''
        add all plants from all accessions
        '''
        acc_ids = [acc.id for acc in accessions]
        stmt = plant_table.select(plant_table.c.accession_id.in_(acc_ids))
        plants = plant_query.from_statement(stmt)
        add_plants(plants)

    # append the objects from the tag
    try:
        from bauble.plugins.tag import Tag
        for obj in objs:
            if isinstance(obj, Tag):
                objs.extend(obj.objects)
    except ImportError:
        pass

    from bauble.plugins.plants import Family, Genus, Species, VernacularName
    from bauble.plugins.garden import Accession, Plant, Location

    for obj in objs:
        # extract the plants from the search results
        if isinstance(obj, Family):
            for gen in obj.genera:
                for sp in gen.species:
                    add_plants_from_accessions(sp.accessions)
        elif isinstance(obj, Genus):
            for sp in obj.species:
                add_plants_from_accessions(sp.accessions)
        elif isinstance(obj, Species):
            add_plants_from_accessions(obj.accessions)
        elif isinstance(obj, VernacularName):
            add_plants_from_accessions(obj.species.accessions)
        elif isinstance(obj, Accession):
            add_plants(obj.plants)
        elif isinstance(obj, Plant):
            add_plants([obj])
        elif isinstance(obj, Location):
            add_plants(obj.plants)

    return all_plants.values()



def get_all_accessions(objs, session=None):
    """
    return all unique accession in objs
    """
    raise NotImplementedError
##     if session == None:
##         session = bauble.Session()
##     from bauble.plugins.plants import Family, Genus, Species, VernacularName
##     from bauble.plugins.garden import Accession, Plant, Location
##     all_accessions = {}
##     def add_accession(accession):
##         if isinstance(accession, Accession):
##             if accession.id not in all_accessions:
##                 all_accessions[accession.id] = accession
##         else:
##             for a in accession
##                 if a.id not in all_accessions
##                     all_accessions[s.id] = s

##     # append the objects from the tag
##     try:
##         from bauble.plugins.tag import Tag
##         for obj in objs:
##             if isinstance(obj, Tag):
##                 objs.extend(obj.objects)
##     except ImportError:
##         pass

##     for obj in objs:
##         if isinstance(obj, Family):
##             for gen in obj.genera:
##                 add_species(gen.speces)
##         elif isinstance(obj, Genus):
##             add_species(obj.species)
##         elif isinstance(obj, Species):
##             add_species(obj)
##         elif isinstance(obj, VernacularName):
##             add_species(obj.species)
##         elif isinstance(obj, Accession):
##             add_species(obj.species)
##         elif isinstance(obj, Plant):
##             add_species(obj.accession.species)
##         elif isinstance(obj, Location):
##             for p in obj.plants:
##                 add_species(p.accession.species)

##     return all_species.values()


## from bauble.plugins.plants import Family, Genus, Species, VernacularName,\
##      species_table, genus_table, family_table

# TODO: would probably be better to create these adapters for each type instead
# of having all these switch statement we would just have a map like....
#adapters = {Family: FamilyAdapter,
#            Genus: GenusAdapter}
# ....or even something like
## species_id_queries = {Family:
##                       select([species_table.c.id], from_obj=[species_table.join(genus_table).join(family_table, family_table.c.id==bindparam('id')]),
##                       Genus:
##                       select([species_table.c.id], from_obj=[species_table.join(genus_table, genus_table.c.id==bindparam('id'))])
##                              }
#
# ... though we really should just be able to generate a big fucking query that
# returns us exactly what we want and let the database do all the work, this
# is really the best way and would take time to create but would be the faster
# and would require the least amount of code, this still means we might have
# to create some sort of map like...

try:
    from bauble.plugins.plants import Species, species_table, Genus, \
         genus_table, Family, family_table, VernacularName
    from bauble.plugins.garden import Accession, accession_table, Plant, \
         plant_table, Location

    species_queries = {
        Family: species_table.join(genus_table).join(family_table, and_(family_table.c.id==bindparam('id'), family_table.c.id==genus_table.c.family_id)),
        Genus: species_table.join(genus_table, and_(genus_table.c.id==species_table.c.genus_id, genus_table.c.id==bindparam('id'))),
        Species: lambda s: s.id,
        VernacularName: lambda vn: vn.species_id,
        Plant: species_table.join(accession_table).join(plant_table, and_(plant_table.c.id==bindparam('id'), accession_table.c.id==plant_table.c.accession_id)),
        Accession: lambda a: a.species_id,
        Location: species_table.join(accession_table).join(plant_table, and_(plant_table.c.location_id==bindparam('id'), accession_table.c.id==plant_table.c.accession_id)),
#                   Tag: []
        }
    def get_all_species(objs, session=None):
        if session == None:
            session = bauble.Session()
        return [session.load(Species, s) for s in _get_all_species_ids(objs)]


    def _get_all_species_ids(objs):
        """
        returns a list of species ids
        """
        species_ids = []
        for obj in objs:
            query = species_queries[type(obj)]
            if callable(query):
                species_ids.append([query(obj)])
            else:
                result = select([species_table.c.id],
                                from_obj=[query]).execute(id=obj.id)
                species_ids.append([r[0] for r in result])
        from itertools import chain
        all_ids = []
        for s in chain(*species_ids):
            if s not in all_ids:
                all_ids.append(s)
        return all_ids

except ImportError, e:
    warning(e)



class SettingsBox(gtk.VBox):
    """
    the interface to use for the settings box, formatters should
    implement this interface and return it from the formatters's get_settings
    method
    """
    def __init__(self):
        super(SettingsBox, self).__init__()

    def get_settings(self):
        raise NotImplementerError

    def update(self, settings={}):
        raise NotImplementerError



class FormatterPlugin(pluginmgr.Plugin):
    '''
    an interface class that a plugin should implement if it wants to generate
    reports with the ReportToolPlugin

    NOTE: the title class attribute must be a unique string
    '''

    title = ''

    @staticmethod
    def get_settings_box():
        '''
        return a class the implement gtk.Box that should hold the gui for
        the formatter
        '''
        raise NotImplementedError

    @staticmethod
    def format(selfobjs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError



class ReportToolDialogView(object):

    def __init__(self):
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(),
                                   "plugins", "report", 'report.glade'))
        self.dialog = self.widgets.report_dialog
        self.dialog.set_transient_for(bauble.gui.window)


    def start(self):
        return self.dialog.run()



class ReportToolDialogPresenter(object):

    formatter_class_map = {} # title->class map

    def __init__(self, view):
        self.view = view
        self.init_names_combo()
        self.init_formatter_combo()

        self.view.widgets.new_button.connect('clicked',
                                             self.on_new_button_clicked)
        self.view.widgets.remove_button.connect('clicked',
                                                self.on_remove_button_clicked)
        self.view.widgets.names_combo.connect('changed',
                                              self.on_names_combo_changed)
        self.view.widgets.formatter_combo.connect('changed',
                                               self.on_formatter_combo_changed)
        self.view.widgets.ok_button.set_sensitive(False)

        # set the names combo to the default, on_names_combo_changes should
        # do the rest of the work
        combo = self.view.widgets.names_combo
        default = prefs[default_config_pref]
        try:
            self.set_names_combo(default)
        except Exception, e:
#            debug('init: %s' % e)
            self.set_names_combo(0)


    def set_names_combo(self, val):
        """
        set the names combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo

        if the model on the combo is None then this method will return
        and not emit the changed signal
        """
#        debug('set_names_combo(%s)' %  val)
        combo = self.view.widgets.names_combo
        if combo.get_model() is None:
#            debug('--None')
            self.view.widgets.details_box.set_sensitive(False)
            return
        if isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)
        combo.emit('changed')


    def set_formatter_combo(self, val):
        """
        set the formatter combo to val and emit the 'changed' signal,
        @param val: either an integer index or a string value in the combo
        combo = self.view.widgets.formatter_combo
        """
        combo = self.view.widgets.formatter_combo
        if isinstance(val, int):
            combo.set_active(val)
        else:
            utils.combo_set_active_text(combo, val)
        combo.emit('changed')


    def set_prefs_for(self, name, formatter_title, settings):
        '''
        this will overwrite any other report settings with name
        '''
#        debug('set_prefs_for(%s, %s, %s)' % (name, formatter_title, settings))
        formatters = prefs[config_list_pref]
        if formatters is None:
            formatters = {}
        formatters[name] = formatter_title, settings
        prefs[config_list_pref] = formatters
#        debug(prefs[config_list_pref])


    def on_new_button_clicked(self, *args):
        # TODO: don't set the OK button as sensitive in the name dialog
        # if the name already exists
        # TOD0: make "Enter" in the entry fire the default response
        d = gtk.Dialog('', self.view.dialog,
                       gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                       buttons=((gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                      gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT)))
        d.vbox.set_spacing(10)
        label = gtk.Label(_('Enter a name for the new formatter'))
        label.set_padding(10, 10)
        d.vbox.pack_start(label)
        entry = gtk.Entry()
        d.vbox.pack_start(entry)
        d.show_all()
        names_model = self.view.widgets.names_combo.get_model()
        while True:
            if d.run() == gtk.RESPONSE_ACCEPT:
                name = entry.get_text()
                if name == '':
                    continue
                elif names_model is not None \
                         and utils.tree_model_has(names_model, name):
                    utils.message_dialog(_('%s already exists') % name)
                    continue
                else:
                    self.set_prefs_for(entry.get_text(), None, {})
                    self.populate_names_combo()
                    utils.combo_set_active_text(self.view.widgets.names_combo,
                                                name)
                    break
            else:
                break
        d.destroy()


    def on_remove_button_clicked(self, *args):
        formatters = prefs[config_list_pref]
        names_combo = self.view.widgets.names_combo
        name = names_combo.get_active_text()
        formatters.pop(name)
        prefs[config_list_pref] = formatters
        self.populate_names_combo()
        names_combo.set_active(0)


    def on_names_combo_changed(self, combo, *args):
        if combo.get_model() is None:
            self.view.widgets.details_box.set_sensitive(False)
            return

        name = combo.get_active_text()
        formatters = prefs[config_list_pref]
        self.view.widgets.details_box.set_sensitive(name is not None)
        prefs[default_config_pref] = name # set the default to the new name
        try:
            title, settings = formatters[name]
        except (KeyError, TypeError), e:
            # TODO: show a dialog saying that you can't find whatever
            # you're looking for in the settings
            debug(e)
            return

        try:
            self.set_formatter_combo(title)
        except Exception, e:
            # TODO: show a dialog saying that you can't find whatever
            # you're looking for in the settings
            debug(e)
            self.set_formatter_combo(-1)
        self.view.widgets.details_box.set_sensitive(True)


    def on_formatter_combo_changed(self, combo, *args):
        '''
        formatter_combo changed signal handler
        '''
        self.view.widgets.ok_button.set_sensitive(False)
        gobject.idle_add(self._formatter_combo_changed_idle, combo)


    def _formatter_combo_changed_idle(self, combo):
        title = combo.get_active_text()
        # main loop never has a chance to change sensitivity, maybe we could
        # do some of this in idle function
        #
        name = self.view.widgets.names_combo.get_active_text()
        try:
            saved_title, settings = prefs[config_list_pref][name]
            if saved_title != title:
                settings = {}
#            debug('settings: %s' % settings)
#            # set the new formatter value in the preferences
#            set_prefs_for(name, self.formatter_class_map[title])
#            #prefs[config_list_pref][name] = title, settings
        except KeyError, e:
            debug(e)
            return

        expander = self.view.widgets.settings_expander
        child = expander.get_child()
        if child is not None:
            expander.remove(child)

        #self.widgets.ok_button.set_sensitive(title is not None)
        self.view.widgets.ok_button.set_sensitive(title is not None)
        if title is None:
            return
        try:
            cls = self.formatter_class_map[title]
        except KeyError:
            return
        box = cls.get_settings_box()
        if box is not None:
            box.update(settings)
            expander.add(box)
            box.show_all()
        expander.set_sensitive(box is not None)
        # TODO: should probably remember expanded state,
        # see formatter_settings_expander_pref
        expander.set_expanded(box is not None)
        title = combo.get_active_text()
        self.set_prefs_for(name, title, settings)
        self.view.widgets.ok_button.set_sensitive(True)


    def init_formatter_combo(self):
        plugins = []
        for p in pluginmgr.plugins:
            if issubclass(p, FormatterPlugin):
                plugins.append(p)

        # we should always have at least the default formatter
        model = gtk.ListStore(str)
        #assert len(plugins) is not 0, 'No formatter plugins defined.'
        if len(plugins) == 0:
            utils.message_dialog(_('No formatter plugins defined'),
                                 gtk.MESSAGE_WARNING)
            return

        for item in plugins:
            title = item.title
            self.formatter_class_map[title] = item
            model.append([item.title])
        self.view.widgets.formatter_combo.set_model(model)


    def populate_names_combo(self):
        '''
        populates the combo with the list of configuration names
        from the prefs
        '''
        configs = prefs[config_list_pref]
        combo = self.view.widgets.names_combo
        if configs is None:
#            debug('configs is None')
            self.view.widgets.details_box.set_sensitive(False)
            utils.clear_model(combo)
            return
        try:
            model = gtk.ListStore(str)
            for cfg in configs.keys():
#                debug('cfg: %s' % cfg)
                model.append([cfg])
            combo.set_model(model)
        except AttributeError, e:
            # no formatters
            debug(e)
            pass


    def init_names_combo(self):
	formatters = prefs[config_list_pref]
	if formatters is None or len(formatters) == 0:
	    msg = _('No formatters found. To create a new formatter click '\
                    'the "New" button.')
	    utils.message_dialog(msg, parent=self.view.dialog)
#	    debug('names_combo.model=None')
	    self.view.widgets.names_combo.set_model(None)
        self.populate_names_combo()


    def save_formatter_settings(self):
        name = self.view.widgets.names_combo.get_active_text()
        title, dummy =  prefs[config_list_pref][name]
        box = self.view.widgets.settings_expander.get_child()
        formatters = prefs[config_list_pref]
#        debug('save_formatter_settings: %s: %s, %s' % (name, title, box.get_settings()))
        formatters[name] = title, box.get_settings()
        prefs[config_list_pref] = formatters
#        debug(prefs[config_list_pref][name])


    def start(self):
        formatter = None
        settings = None
        while True:
            response = self.view.start()
            if response == gtk.RESPONSE_OK:
                # get format method
                # save default
                prefs[default_config_pref] = \
                             self.view.widgets.names_combo.get_active_text()
                self.save_formatter_settings()
                name = self.view.widgets.names_combo.get_active_text()
                title, settings =  prefs[config_list_pref][name]
                formatter = self.formatter_class_map[title]
                break
            else:
                break
        self.view.dialog.destroy()
        return formatter, settings



class ReportToolDialog(object):

    def __init__(self):
        self.view = ReportToolDialogView()
        self.presenter = ReportToolDialogPresenter(self.view)


    def start(self):
        return self.presenter.start()



class ReportTool(pluginmgr.Tool):

    label = "Report"

    @classmethod
    def start(self):
        '''
        '''
        # get the select results from the search view
        from bauble.view import SearchView
        view = bauble.gui.get_view()
        if not isinstance(view, SearchView):
            utils.message_dialog(_('Search for something first.'))
            return

        model = view.results_view.get_model()
        if model is None:
            utils.message_dialog(_('Search for something first.'))
            return

        bauble.set_busy(True)
        ok = False
        try:
            while True:
                dialog = ReportToolDialog()
                formatter, settings = dialog.start()
                if formatter is None:
                    break
                ok = formatter.format([row[0] for row in model], **settings)
                if ok:
                    break

        except AssertionError, e:
            debug(e)
            parent = None
            if hasattr(self, 'view') and hasattr(self.view, 'dialog'):
                parent = self.view.dialog

            utils.message_details_dialog(str(e), traceback.format_exc(),
                                         gtk.MESSAGE_ERROR, parent=parent)
        except Exception:
            debug(traceback.format_exc())
            utils.message_details_dialog(_('Formatting Error'),
                                     traceback.format_exc(), gtk.MESSAGE_ERROR)
        bauble.set_busy(False)
        return



class ReportToolPlugin(pluginmgr.Plugin):
    '''
    '''
    tools = [ReportTool]



def plugin():
    from bauble.plugins.report.default import DefaultFormatterPlugin
    return [ReportToolPlugin, DefaultFormatterPlugin]


