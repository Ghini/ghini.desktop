#
# Species table definition
#
import os
import sys
from operator import itemgetter
import traceback
import weakref
import xml.sax.saxutils as sax

import gtk
import gobject
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import SQLError

import bauble
from bauble.prefs import prefs
import bauble.utils as utils
import bauble.paths as paths
import bauble.editor as editor
from bauble.utils.log import debug
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus, GenusSynonym
from bauble.plugins.plants.species_model import Species, \
    SpeciesSynonym, VernacularName, DefaultVernacularName, \
    SpeciesDistribution, SpeciesNote, Geography, infrasp_rank_values


class SpeciesEditorPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_GENUS = 1

    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_hybrid_check': 'hybrid',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_spqual_combo': 'sp_qual',
                           }


    def __init__(self, model, view):
        super(SpeciesEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)
        self.__dirty = False
        self.init_fullname_widgets()
        self.vern_presenter = VernacularNamePresenter(self)
        self.synonyms_presenter = SynonymsPresenter(self)
        self.dist_presenter = DistributionPresenter(self)
        self.infrasp_presenter = InfraspPresenter(self)

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = \
            editor.NotesPresenter(self, 'notes', notes_parent)
        self.refresh_view()

        # connect signals
        def gen_get_completions(text):
            clause = utils.ilike(Genus.genus, '%s%%' % unicode(text))
            return self.session.query(Genus).filter(clause)

        # called a genus is selected from the genus completions
        def on_select(value):
            #debug('on select: %s' % value)
            for kid in self.view.widgets.message_box_parent.get_children():
                self.view.widgets.remove_parent(kid)
            self.set_model_attr('genus', value)
            if not value:
                return
            syn = self.session.query(GenusSynonym).\
                filter(GenusSynonym.synonym_id == value.id).first()
            if not syn:
                self.set_model_attr('genus', value)
                return
            msg = _('The genus <b>%(synonym)s</b> is a synonym of '\
                        '<b>%(genus)s</b>.\n\nWould you like to choose '\
                        '<b>%(genus)s</b> instead?' \
                        % {'synonym': syn.synonym, 'genus': syn.genus})
            box = None
            def on_response(button, response):
                self.view.widgets.remove_parent(box)
                box.destroy()
                if response:
                    self.view.widgets.sp_genus_entry.\
                        set_text(utils.utf8(syn.genus))
                    self.set_model_attr('genus', syn.genus)
                else:
                    self.set_model_attr('genus', value)
            box = utils.add_message_box(self.view.widgets.message_box_parent,
                                        utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()

        self.assign_completions_handler('sp_genus_entry', #'genus',
                                        gen_get_completions,
                                        on_select=on_select)
        self.assign_simple_handler('sp_species_entry', 'sp',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_hybrid_check', 'hybrid')
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual')
        self.assign_simple_handler('sp_author_entry', 'sp_author',
                                   editor.UnicodeOrNoneValidator())



    def __del__(self):
        # we have to delete the views in the child presenters manually
        # to avoid the circular reference
        del self.vern_presenter.view
        del self.synonyms_presenter.view
        del self.dist_presenter.view
        del self.notes_presenter.view
        del self.infrasp_presenter.view


    def dirty(self):
        return self.__dirty or self.session.is_modified(self.model) or \
            self.vern_presenter.dirty() or self.synonyms_presenter.dirty() or \
            self.dist_presenter.dirty() or self.infrasp_presenter.dirty() or \
            self.notes_presenter.dirty()


    def set_model_attr(self, field, value, validator=None):
        '''
        Resets the sensitivity on the ok buttons and the name widgets
        when values change in the model
        '''
        super(SpeciesEditorPresenter, self).set_model_attr(field, value,
                                                           validator)
        self.__dirty = True
        sensitive = True
        if len(self.problems) != 0 \
           or len(self.vern_presenter.problems) != 0 \
           or len(self.synonyms_presenter.problems) != 0 \
           or len(self.dist_presenter.problems) != 0:
            sensitive = False
        elif not (self.model.genus and self.model.sp):
            sensitive = False
        # elif not (self.model.sp or self.model.cv_group or \
        #             (self.model.infrasp_rank == 'cv.' and self.model.infrasp)):
        #     sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)


    def refresh_sensitivity(self):
        """
        :param self:
        """
        sensitive = False
        if self.dirty():
            sensitive = True
        self.view.set_accept_buttons_sensitive(sensitive)


    def init_fullname_widgets(self):
        '''
        initialized the signal handlers on the widgets that are relative to
        building the fullname string in the sp_fullname_label widget
        '''
        self.refresh_fullname_label()
        refresh = lambda *args: self.refresh_fullname_label()
        widgets = ['sp_genus_entry', 'sp_species_entry', 'sp_author_entry',
                   'sp_cvgroup_entry', 'sp_spqual_combo']
        for widget_name in widgets:
            w = self.view.widgets[widget_name]
            self.view.connect_after(widget_name, 'changed', refresh)
        self.view.connect_after('sp_hybrid_check', 'toggled', refresh)


    def refresh_fullname_label(self):
        '''
        set the value of sp_fullname_label to either '--' if there
        is a problem or to the name of the string returned by Species.str
        '''
        if len(self.problems) > 0 or self.model.genus == None:
            self.view.widgets.sp_fullname_label.set_markup('--')
            return
        sp_str = Species.str(self.model, markup=True, authors=True)
        self.view.widgets.sp_fullname_label.set_markup(sp_str)


    def start(self):
        r = self.view.start()
        return r


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            if field is 'genus_id':
                value = self.model.genus
            else:
                value = getattr(self.model, field)
#            debug('%s, %s, %s' % (widget, field, value))
#            self.view.set_widget_value(widget, value,
#                                       default=self.defaults.get(field, None))
            self.view.set_widget_value(widget, value)
        self.vern_presenter.refresh_view(self.model.default_vernacular_name)
        self.synonyms_presenter.refresh_view()
        self.dist_presenter.refresh_view()



class InfraspPresenter(editor.GenericEditorPresenter):
    """
    """

    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super(InfraspPresenter, self).__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self._dirty = False
        self.view.connect('add_infrasp_button', "clicked", self.append_infrasp)

        # will table.resize() remove the children??
        table = self.view.widgets.infrasp_table
        for item in self.view.widgets.infrasp_table.get_children():
            if not isinstance(item, gtk.Label):
                self.view.widgets.remove_parent(item)

        self.table_rows = []
        for index in range(1,5):
            infrasp = self.model.get_infrasp(index)
            if infrasp != (None, None, None):
                self.append_infrasp()


    def dirty(self):
        return self._dirty


    def append_infrasp(self, *args):
        """
        """
        # TODO: it is very slow to add rows to the widget...maybe if
        # we disable event on the table until all the rows have been
        # added
        level = len(self.table_rows)+1
        row = InfraspPresenter.Row(self, level)
        self.table_rows.append(row)
        if level >= 4:
            self.view.widgets.add_infrasp_button.props.sensitive = False
        return row


    class Row(object):

        def __init__(self, presenter, level):
            """
            """
            self.presenter = presenter
            self.species = presenter.model
            table = self.presenter.view.widgets.infrasp_table
            nrows = table.props.n_rows
            ncols = table.props.n_columns
            self.level = level

            rank, epithet, author = self.species.get_infrasp(self.level)

            # rank combo
            self.rank_combo = gtk.ComboBox()
            self.presenter.init_translatable_combo(self.rank_combo,
                                                   infrasp_rank_values)
            utils.set_widget_value(self.rank_combo, rank)
            self.rank_combo.connect('changed', self.on_rank_combo_changed)
            table.attach(self.rank_combo, 0, 1, level, level+1,
                         xoptions=gtk.FILL, yoptions=-1)

            # epithet entry
            self.epithet_entry = gtk.Entry()
            utils.set_widget_value(self.epithet_entry, epithet)
            self.epithet_entry.connect('changed',
                                       self.on_epithet_entry_changed)
            table.attach(self.epithet_entry, 1, 2, level, level+1,
                         xoptions=gtk.FILL|gtk.EXPAND, yoptions=-1)

            # author entry
            self.author_entry = gtk.Entry()
            utils.set_widget_value(self.author_entry, author)
            self.author_entry.connect('changed', self.on_author_entry_changed)
            table.attach(self.author_entry, 2, 3, level, level+1,
                         xoptions=gtk.FILL|gtk.EXPAND, yoptions=-1)

            self.remove_button = gtk.Button()#stock=gtk.STOCK_ADD)
            img = gtk.image_new_from_stock(gtk.STOCK_REMOVE,
                                           gtk.ICON_SIZE_BUTTON)
            self.remove_button.props.image = img
            self.remove_button.connect('clicked',
                                       self.on_remove_button_clicked)
            table.attach(self.remove_button, 3, 4, level, level+1,
                         xoptions=gtk.FILL, yoptions=-1)
            table.show_all()


        def on_remove_button_clicked(self, *args):
            # remove the widgets
            table = self.presenter.view.widgets.infrasp_table

            # remove the infrasp from the species and reset the levels
            # on the remaining infrasp that have a higher level than
            # the one being deleted
            table.remove(self.rank_combo)
            table.remove(self.epithet_entry)
            table.remove(self.author_entry)
            table.remove(self.remove_button)

            self.set_model_attr('rank', None)
            self.set_model_attr('epithet', None)
            self.set_model_attr('author', None)

            # move all the infrasp values up a level
            for i in range(self.level+1, 5):
                rank, epithet, author = self.species.get_infrasp(i)
                self.species.set_infrasp(i-1, rank, epithet, author)

            self.presenter._dirty = False
            self.presenter.parent_ref().refresh_fullname_label()
            self.presenter.parent_ref().refresh_sensitivity()
            self.presenter.view.widgets.add_infrasp_button.props.\
                sensitive = True


        def set_model_attr(self, attr, value):
            infrasp_attr = Species.infrasp_attr[self.level][attr]
            setattr(self.species, infrasp_attr, value)
            self.presenter._dirty = False
            self.presenter.parent_ref().refresh_fullname_label()
            self.presenter.parent_ref().refresh_sensitivity()


        def on_rank_combo_changed(self, combo, *args):
            model = combo.get_model()
            it = combo.get_active_iter()
            self.set_model_attr('rank', utils.utf8(model[it][0]))


        def on_epithet_entry_changed(self, entry, *args):
            value = utils.utf8(entry.props.text)
            if not value: # if None or ''
                value = None
            self.set_model_attr('epithet', value)


        def on_author_entry_changed(self, entry, *args):
            value = utils.utf8(entry.props.text)
            if not value: # if None or ''
                value = None
            self.set_model_attr('author', value)



class DistributionPresenter(editor.GenericEditorPresenter):
    """
    """

    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super(DistributionPresenter, self).__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self.__dirty = False
        self.add_menu = gtk.Menu()
        self.add_menu.attach_to_widget(self.view.widgets.sp_dist_add_button,
                                       None)
        self.remove_menu = gtk.Menu()
        self.remove_menu.attach_to_widget(self.view.widgets.sp_dist_remove_button,
                                          None)
        self.view.connect('sp_dist_add_button', 'button-press-event',
                          self.on_add_button_pressed)
        self.view.connect('sp_dist_remove_button', 'button-press-event',
                          self.on_remove_button_pressed)
        self.init_add_button()


    def refresh_view(self):
        label = self.view.widgets.sp_dist_label
        s = ', '.join([str(d) for d in self.model.distribution])
        label.set_text(s)


    def on_add_button_pressed(self, button, event):
        self.add_menu.popup(None, None, None, event.button, event.time)


    def on_remove_button_pressed(self, button, event):
        # clear the menu
        for c in self.remove_menu.get_children():
            self.remove_menu.remove(c)
        # add distributions to menu
        for dist in self.model.distribution:
            item = gtk.MenuItem(str(dist))
            self.view.connect(item, 'activate',
                              self.on_activate_remove_menu_item, dist)
            self.remove_menu.append(item)
        self.remove_menu.show_all()
        self.remove_menu.popup(None, None, None, event.button, event.time)


    def on_activate_add_menu_item(self, widget, geoid=None):
        from bauble.plugins.plants.species_model import Geography
        geo = self.session.query(Geography).filter_by(id=geoid).one()
        # check that this geography isn't already in the distributions
        if geo in [d.geography for d in self.model.distribution]:
#            debug('%s already in %s' % (geo, self.model))
            return
        dist = SpeciesDistribution(geography=geo)
        self.model.distribution.append(dist)
#        debug([str(d) for d in self.model.distribution])
        self.__dirty = True
        self.refresh_view()
        self.parent_ref().refresh_sensitivity()


    def on_activate_remove_menu_item(self, widget, dist):
        self.model.distribution.remove(dist)
        utils.delete_or_expunge(dist)
        self.refresh_view()
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def dirty(self):
        return self.__dirty


    def init_add_button(self):
        self.view.widgets.sp_dist_add_button.set_sensitive(False)
        geography_table = Geography.__table__
        geos = select([geography_table.c.id, geography_table.c.name,
                       geography_table.c.parent_id]).execute().fetchall()
        geos_hash = {}
        # TODO: i think the geo_hash should be calculated in an idle
        # function so that starting the editor isn't delayed while the
        # hash is being built
        for geo_id, name, parent_id in geos:
            try:
                geos_hash[parent_id].append((geo_id, name))
            except KeyError:
                geos_hash[parent_id] = [(geo_id, name)]

        for kids in geos_hash.values():
            kids.sort(key=itemgetter(1)) # sort by name

        def get_kids(pid):
            try:
                return geos_hash[pid]
            except KeyError:
                return []

        def has_kids(pid):
            try:
                return len(geos_hash[pid]) > 0
            except KeyError:
                return False

        def build_menu(geo_id, name):
            item = gtk.MenuItem(name)
            if not has_kids(geo_id):
                if item.get_submenu() is None:
                    self.view.connect(item, 'activate',
                                      self.on_activate_add_menu_item, geo_id)
                return item

            kids_added = False
            submenu = gtk.Menu()
            # removes two levels of kids with the same name, there must be a
            # better way to do this but i got tired of thinking about it
            kids = get_kids(geo_id)
            if len(kids) > 0:
                kids_added = True
            for kid_id, kid_name in kids:#get_kids(geo_id):
                submenu.append(build_menu(kid_id, kid_name))

            if kids_added:
                sel_item = gtk.MenuItem(name)
                submenu.insert(sel_item, 0)
                submenu.insert(gtk.SeparatorMenuItem(), 1)
                item.set_submenu(submenu)
                self.view.connect(sel_item, 'activate',
                                  self.on_activate_add_menu_item, geo_id)
            else:
                self.view.connect(item, 'activate',
                                  self.on_activate_add_menu_item, geo_id)
            return item

        def populate():
            """
            add geography value to the menu, any top level items that don't
            have any kids are appended to the bottom of the menu
            """
            if not geos_hash:
                # we should really only get here when running the
                # species editor as a unit test since then the
                # geography table probably isn't populated
                return
            no_kids = []
            for geo_id, geo_name in geos_hash[None]:
                if geo_id not in geos_hash.keys():
                    no_kids.append((geo_id, geo_name))
                else:
                    self.add_menu.append(build_menu(geo_id, geo_name))

            for geo_id, geo_name in sorted(no_kids):
                self.add_menu.append(build_menu(geo_id, geo_name))

            self.add_menu.show_all()
            self.view.widgets.sp_dist_add_button.set_sensitive(True)
        gobject.idle_add(populate)



class VernacularNamePresenter(editor.GenericEditorPresenter):
    # TODO: change the background of the entries and desensitize the
    # name/lang entries if the name conflicts with an existing vernacular
    # name for this species
    """
    in the VernacularNamePresenter we don't really use self.model, we
    more rely on the model in the TreeView which are VernacularName
    objects
    """
    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super(VernacularNamePresenter, self).__init__(parent.model,parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self.__dirty = False
        self.init_treeview(self.model.vernacular_names)
        self.view.connect('sp_vern_add_button', 'clicked',
                          self.on_add_button_clicked)
        self.view.connect('sp_vern_remove_button', 'clicked',
                          self.on_remove_button_clicked)


    def dirty(self):
        """
        @return True or False if the vernacular names have changed.
        """
        return self.__dirty


    def on_add_button_clicked(self, button, data=None):
        """
        Add the values in the entries to the model.
        """
        treemodel = self.treeview.get_model()
        column = self.treeview.get_column(0)
        vn = VernacularName()
        self.model.vernacular_names.append(vn)
        treeiter = treemodel.append([vn])
        path = treemodel.get_path(treeiter)
        self.treeview.set_cursor(path, column, start_editing=True)
        if len(treemodel) == 1:
            #self.set_model_attr('default_vernacular_name', vn)
            self.model.default_vernacular_name = vn


    def on_remove_button_clicked(self, button, data=None):
        """
        Removes the currently selected vernacular name from the view.
        """
        tree = self.view.widgets.vern_treeview
        path, col = tree.get_cursor()
        treemodel = tree.get_model()
        vn = treemodel[path][0]

        msg = _('Are you sure you want to remove the vernacular ' \
                    'name <b>%s</b>?') % utils.xml_safe_utf8(vn.name)
        if vn.name and not vn in self.session.new and not \
                utils.yes_no_dialog(msg, parent=self.view.get_window()):
            return

        treemodel.remove(treemodel.get_iter(path))
        self.model.vernacular_names.remove(vn)
        utils.delete_or_expunge(vn)
        if not self.model.default_vernacular_name:
            # if there is only one value in the tree then set it as the
            # default vernacular name
            first = treemodel.get_iter_first()
            if first:
#                 self.set_model_attr('default_vernacular_name',
#                                     tree_model[first][0])
                self.model.default_vernacular_name = treemodel[first][0]
        self.parent_ref().refresh_sensitivity()
        self.__dirty = True


    def on_default_toggled(self, cell, path, data=None):
        """
        Default column callback.
        """
        active = cell.get_active()
        if not active: # then it's becoming active
            vn = self.treeview.get_model()[path][0]
            self.set_model_attr('default_vernacular_name', vn)
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def on_cell_edited(self, cell, path, new_text, prop):
        treemodel = self.treeview.get_model()
        vn = treemodel[path][0]
        if getattr(vn, prop) == new_text:
            return  # didn't change
        setattr(vn, prop, utils.utf8(new_text))
        self.__dirty = True
        self.parent_ref().refresh_sensitivity()


    def init_treeview(self, model):
        """
        Initialized the list of vernacular names.

        The columns and cell renderers are loaded from the .glade file
        so we just need to customize them a bit.
        """
        self.treeview = self.view.widgets.vern_treeview

        def _name_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', v.name)
            # just added so change the background color to indicate its new
#            if not v.isinstance:
            if v.id is None: # hasn't been committed
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        column = self.view.widgets.vn_name_column
        #column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        cell = self.view.widgets.vn_name_cell
        self.view.widgets.vn_name_column.\
            set_cell_data_func(cell, _name_data_func)
        self.view.connect(cell, 'edited', self.on_cell_edited, 'name')

        def _lang_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', v.language)
            # just added so change the background color to indicate its new
            #if not v.isinstance:`
            if v.id is None: # hasn't been committed
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = self.view.widgets.vn_lang_cell
        self.view.widgets.vn_lang_column.\
            set_cell_data_func(cell, _lang_data_func)
        self.view.connect(cell, 'edited', self.on_cell_edited, 'language')

        def _default_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            try:
                cell.set_property('active',
                                  v==self.model.default_vernacular_name)
                return
            except AttributeError, e:
                pass
            cell.set_property('active', False)

        cell = self.view.widgets.vn_default_cell
        self.view.widgets.vn_default_column.\
            set_cell_data_func(cell, _default_data_func)

        utils.clear_model(self.treeview)

        # add the vernacular names to the tree
        tree_model = gtk.ListStore(object)
        for vn in model:
            tree_model.append([vn])
        self.treeview.set_model(tree_model)

        self.view.connect(self.treeview, 'cursor-changed',
                          self.on_tree_cursor_changed)


    def on_tree_cursor_changed(self, tree, data=None):
        path, column = tree.get_cursor()
        self.view.widgets.sp_vern_remove_button.set_sensitive(True)


    def refresh_view(self, default_vernacular_name):
        tree_model = self.treeview.get_model()
        #if len(self.model) > 0 and default_vernacular_name is None:
        vernacular_names = self.model.vernacular_names
        default_vernacular_name = self.model.default_vernacular_name
        if len(vernacular_names) > 0 and default_vernacular_name is None:
            msg = 'This species has vernacular names but none of them are '\
                  'selected as the default. The first vernacular name in the '\
                  'list has been automatically selected.'
            utils.message_dialog(msg)
            first = tree_model.get_iter_first()
            value = tree_model[first][0]
            path = tree_model.get_path(first)
            #self.set_model_attr('default_vernacular_name', value)
            self.model.default_vernacular_name = value
            debug(self.model.default_vernacular_name)
            self.__dirty = True
            self.parent_ref().refresh_sensitivity()
        elif default_vernacular_name is None:
            return



class SynonymsPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1

    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super(SynonymsPresenter, self).__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self.init_treeview()
        debug(self.problems)
        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = SpeciesSynonym()
        def sp_get_completions(text):
            query = self.session.query(Species).join('genus').\
                filter(utils.ilike(Genus.genus, '%s%%' % text)).\
                filter(Species.id != self.model.id)
            return query

        def on_select(value):
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.sp_syn_add_button.set_sensitive(sensitive)
            self._selected = value
        self.assign_completions_handler('sp_syn_entry', sp_get_completions,
                                        on_select=on_select)

        self._selected = None
        self.view.connect('sp_syn_add_button', 'clicked',
                          self.on_add_button_clicked)
        self.view.connect('sp_syn_remove_button', 'clicked',
                          self.on_remove_button_clicked)
        self.__dirty = False


    def dirty(self):
        return self.__dirty


    def init_treeview(self):
        '''
        initialize the gtk.TreeView
        '''
        self.treeview = self.view.widgets.sp_syn_treeview

        def _syn_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', str(v))
            # just added so change the background color to indicate its new
            if not hasattr(v, 'id') or v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)

        col = self.view.widgets.syn_column
        col.set_cell_data_func(self.view.widgets.syn_cell, _syn_data_func)

        utils.clear_model(self.treeview)
        tree_model = gtk.ListStore(object)
        for syn in self.model._synonyms:
            tree_model.append([syn])
        self.treeview.set_model(tree_model)
        self.view.connect(self.treeview, 'cursor-changed',
                          self.on_tree_cursor_changed)


    def on_tree_cursor_changed(self, tree, data=None):
        '''
        '''
        path, column = tree.get_cursor()
        self.view.widgets.sp_syn_remove_button.set_sensitive(True)


    def refresh_view(self):
        """
        doesn't do anything
        """
        return


    def on_add_button_clicked(self, button, data=None):
        """
        adds the synonym from the synonym entry to the list of synonyms for
        this species
        """
        syn = SpeciesSynonym(species=self.model, synonym=self._selected)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._selected = None
        entry = self.view.widgets.sp_syn_entry
        entry.set_text('')
        entry.set_position(-1)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.view.widgets.sp_syn_add_button.set_sensitive(False)
        self.parent_ref().refresh_sensitivity()
        self.__dirty = True


    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database
        tree = self.view.widgets.sp_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]
        s = Species.str(value.synonym, markup=True)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current species?\n\n<i>Note: This will not remove the species '\
              '%s from the database.</i>' % (s, s)
        if utils.yes_no_dialog(msg, parent=self.view.get_window()):
            tree_model.remove(tree_model.get_iter(path))
            self.model.synonyms.remove(value.synonym)
            utils.delete_or_expunge(value)
            # TODO: ** important ** this doesn't respect any unique
            # contraints on the species for synonyms and allow a
            # species to have another species as a synonym multiple
            # times...see below

            # TODO: using session.flush here with an argument is
            # deprecated in SA 0.5 and will probably removed in SA
            # 0.6...but how do we only flush the one value..unless we
            # create a new session, merge it, commit that session,
            # close it and then refresh the same object in
            # self.session

            # make the change in synonym immediately available so that if
            # we try to add the same species again we don't break the
            # SpeciesSynonym UniqueConstraint

            # tmp_session = bauble.Session()
            # tmp_value = tmp.session.merge(value)
            # tmp.session.commit()
            # tmp.session.close()
            # self.session.refresh(value)
            self.session.flush([value])
            self.parent_ref().refresh_sensitivity()
            self.__dirty = True



class SpeciesEditorView(editor.GenericEditorView):

    expanders_pref_map = {}#'sp_infra_expander': 'editor.species.infra.expanded',
                          #}#'sp_meta_expander': 'editor.species.meta.expanded'}

    _tooltips = {
        'sp_genus_entry': _('Genus '),
        'sp_species_entry': _('Species epithet'),
        'sp_author_entry': _('Species author'),
        'sp_hybrid_check': _('Species hybrid flag'),
        'sp_cvgroup_entry': _('Cultivar group'),
        'sp_spqual_combo': _('Species qualifier'),
        'sp_dist_frame': _('Species distribution'),
        'sp_vern_frame': _('Vernacular names'),
        'sp_syn_box': _('Species synonyms')
        }



    def __init__(self, parent=None):
        '''
        the constructor

        @param parent: the parent window
        '''
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'species_editor.glade')
        super(SpeciesEditorView, self).__init__(filename, parent=parent)
        self.attach_completion('sp_genus_entry',
                               self.genus_completion_cell_data_func,
                               match_func=self.genus_match_func)
        self.attach_completion('sp_syn_entry', self.syn_cell_data_func)
        self.set_accept_buttons_sensitive(False)
        self.restore_state()


    def get_window(self):
        '''
        Returns the top level window or dialog.
        '''
        return self.widgets.species_dialog


    @staticmethod
    def genus_match_func(completion, key, iter, data=None):
        """
        match against both str(genus) and str(genus.genus) so that we
        catch the genera with hybrid flags in their name when only
        entering the genus name
        """
        genus = completion.get_model()[iter][0]
        if str(genus).lower().startswith(key.lower()) \
               or str(genus.genus).lower().startswith(key.lower()):
            return True
        return False


    def set_accept_buttons_sensitive(self, sensitive):
        '''
        set the sensitivity of all the accept/ok buttons for the editor dialog
        '''
        self.widgets.sp_ok_button.set_sensitive(sensitive)
        try:
            import bauble.plugins.garden
            self.widgets.sp_ok_and_add_button.set_sensitive(sensitive)
        except Exception:
            pass
        self.widgets.sp_next_button.set_sensitive(sensitive)


    @staticmethod
    def genus_completion_cell_data_func(column, renderer, model, treeiter,
                                        data=None):
        '''
        '''
        v = model[treeiter][0]
        renderer.set_property('text', '%s (%s)' % (Genus.str(v),
                                                   Family.str(v.family)))


    @staticmethod
    def syn_cell_data_func(column, renderer, model, treeiter, data=None):
        '''
        '''
        v = model[treeiter][0]
        renderer.set_property('text', str(v))


    def save_state(self):
        '''
        save the current state of the gui to the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            prefs[pref] = self.widgets[expander].get_expanded()


    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.iteritems():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)


    def start(self):
        '''
        starts the views, essentially calls run() on the main dialog
        '''
        return self.get_window().run()



class SpeciesEditor(editor.GenericModelViewPresenterEditor):

    label = _('Species')
    mnemonic_label = _('_Species')

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model=None, parent=None):
        '''
        @param model: a species instance or None
        @param parent: the parent window or None
        '''
        if model is None:
            model = Species()
        super(SpeciesEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = SpeciesEditorView(parent=self.parent)
        self.presenter = SpeciesEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        # set default focus
        if self.model.genus is None:
            view.widgets.sp_genus_entry.grab_focus()
        else:
            view.widgets.sp_species_entry.grab_focus()


    def handle_response(self, response):
        """
        @return: return True if the editor is realdy to be closes, False if
        we want to keep editing, if any changes are committed they are stored
        in self._committed
        """
        # TODO: need to do a __cleanup_model before the commit to do things
        # like remove the insfraspecific information that's attached to the
        # model if the infraspecific rank is None
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                exc = traceback.format_exc()
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') % \
                        utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                #warning(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = SpeciesEditor(Species(genus=self.model.genus), self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            from bauble.plugins.garden.accession import AccessionEditor, \
                 Accession
            e = AccessionEditor(Accession(species=self.model),
                                parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def commit_changes(self):
        # if self.model.sp or cv_group is empty and
        # self.model.infrasp_rank=='cv.' and self.model.infrasp
        # then show a dialog saying we can't commit and return

        # if self.model.hybrid is None and self.model.infrasp_rank is None:
        #     self.model.infrasp = None
        #     self.model.infrasp_author = None
        #     self.model.cv_group = None

        # remove incomplete vernacular names
        for vn in self.model.vernacular_names:
            if vn.name in (None, ''):
                self.model.vernacular_names.remove(vn)
                utils.delete_or_expunge(vn)
                del vn
        super(SpeciesEditor, self).commit_changes()


    def start(self):
        if self.session.query(Genus).count() == 0:
            msg = 'You must first add or import at least one genus into the '\
                  'database before you can add species.'
            utils.message_dialog(msg)
            return

        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.presenter.cleanup()
        self.session.close() # cleanup session
        return self._committed
