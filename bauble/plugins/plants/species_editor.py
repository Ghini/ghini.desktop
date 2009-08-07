#
# Species table definition
#
import os
import sys
import traceback
import xml.sax.saxutils as sax
from operator import itemgetter

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
from bauble.utils.log import log, debug
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus
from bauble.plugins.plants.species_model import Species, \
     SpeciesSynonym, VernacularName, DefaultVernacularName, \
     SpeciesDistribution, Geography

class SpeciesEditorPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_GENUS = 1

    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_infra_rank_combo': 'infrasp_rank',
                           'sp_hybrid_combo': 'sp_hybrid',
                           'sp_infra_entry': 'infrasp',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_infra_author_entry': 'infrasp_author',
                           'sp_spqual_combo': 'sp_qual',
                           'sp_notes_textview': 'notes'}


    def __init__(self, model, view):
        super(SpeciesEditorPresenter, self).__init__(model, view)
        self.session = object_session(model)

        combos = ('sp_infra_rank_combo', 'sp_hybrid_combo', 'sp_spqual_combo')
        for name in combos:
            self.init_enum_combo(name, self.widget_to_field_map[name])

        self.init_fullname_widgets()
        self.vern_presenter = VernacularNamePresenter(self.model, self.view,
                                                      self.session)
        self.synonyms_presenter = SynonymsPresenter(self.model, self.view,
                                                    self.session)
        self.dist_presenter = DistributionPresenter(self.model,
                                                    self.view, self.session)
        self.refresh_view()

        # connect signals
        def gen_get_completions(text):
            clause = or_(utils.ilike(Genus.genus, '%s%%' % unicode(text)),
                         utils.ilike(Genus.hybrid, '%s%%' % unicode(text)))
            return self.session.query(Genus).filter(clause)

        #def set_in_model(self, field, value):
        #    debug('set_in_model(%s, %s)' % (field, value))
        #    setattr(self.model, field, value)
        def on_select(value):
            self.set_model_attr('genus', value)
        self.assign_completions_handler('sp_genus_entry', #'genus',
                                        gen_get_completions,
                                        on_select=on_select)

        self.assign_simple_handler('sp_species_entry', 'sp',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_infra_rank_combo', 'infrasp_rank')
        self.assign_simple_handler('sp_hybrid_combo', 'sp_hybrid')
        self.assign_simple_handler('sp_infra_entry', 'infrasp',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_infra_author_entry', 'infrasp_author',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual')
        self.assign_simple_handler('sp_author_entry', 'sp_author',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_notes_textview', 'notes',
                                   editor.UnicodeOrNoneValidator())
        self.__dirty = False


    def __del__(self):
        # we have to delete the views in the child presenters manually
        # to avoid the circul reference
        del self.vern_presenter.view
        del self.synonyms_presenter.view
        del self.dist_presenter.view


    def dirty(self):
        return self.__dirty or self.session.is_modified(self.model) or \
            self.vern_presenter.dirty() or self.synonyms_presenter.dirty() or \
            self.dist_presenter.dirty()


    def refresh_sensitivity(self):
        '''
        set the sensitivity on the widgets that make up the species name
        according to values in the model
        '''
        return
        # states_dict:
        # { widget: [list of fields]
        # - if any of fields is None then the widget.sensitive = False
        # - if one of the fields is a tuple then the values in the
        # tuple are AND'd together to determine the widgets
        # sensitivity, e.g. all of the widgets in the tuple have to be
        # not None
#         states_dict = {'sp_hybrid_combo': [('genus', 'genus')],
#                        'sp_species_entry': [('genus', 'genus')],
#                        'sp_author_entry': ['sp'],
#                        'sp_infra_rank_combo': ['sp'],
#                        'sp_infra_entry': [('infrasp_rank', 'sp_hybrid'), 'sp'],
#                        'sp_infra_author_entry': [('infrasp_rank', 'sp_hybrid'),
#                                                  'infrasp', 'sp']}
        states_dict = {'sp_hybrid_combo': ['genus'],
                       'sp_species_entry': ['genus'],
                       'sp_author_entry': ['sp'],
                       'sp_infra_rank_combo': ['sp'],
                       'sp_infra_entry': [('infrasp_rank', 'sp_hybrid'), 'sp'],
                       'sp_infra_author_entry': [('infrasp_rank', 'sp_hybrid'),
                                                 'infrasp', 'sp']}
        for widget, fields in states_dict.iteritems():
            sensitive = False
            for field in fields:
                if isinstance(field, tuple):
                    if None not in [getattr(self.model, f) for f in field]:
                        sensitive = True
                        break
                elif getattr(self.model, field) is not None:
                    sensitive = True
                    break
            self.view.widgets[widget].set_sensitive(sensitive)


        # turn off the infraspecific rank combo if the hybrid value in the
        # model is not None, this has to be called before the conditional that
        # sets the sp_cvgroup_entry
#        if self.model.sp_hybrid is not None:
#            self.view.widgets.sp_infra_rank_combo.set_sensitive(False)

        # infraspecific rank has to be a cultivar for the cultivar group entry
        # to be sensitive
        if self.model.infrasp_rank == 'cv.' \
               and self.view.widgets['sp_infra_rank_combo'].get_property('sensitive'):
            self.view.widgets.sp_cvgroup_entry.set_sensitive(True)
        else:
            self.view.widgets.sp_cvgroup_entry.set_sensitive(False)



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
        elif not self.model.genus:
            sensitive = False
        elif not (self.model.sp or self.model.cv_group or \
                    (self.model.infrasp_rank == 'cv.' and self.model.infrasp)):
            sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)
        self.refresh_sensitivity()


    def init_fullname_widgets(self):
        '''
        initialized the signal handlers on the widgets that are relative to
        building the fullname string in the sp_fullname_label widget
        '''
        self.refresh_fullname_label()
        def on_insert(entry, *args):
            self.refresh_fullname_label()
        def on_delete(entry, *args):
            self.refresh_fullname_label()
        for widget_name in ['sp_genus_entry', 'sp_species_entry',
                            'sp_author_entry', 'sp_infra_entry',
                            'sp_cvgroup_entry', 'sp_infra_author_entry']:
            w = self.view.widgets[widget_name]
            self.view.connect_after(widget_name, 'insert-text', on_insert)
            self.view.connect_after(widget_name, 'delete-text', on_delete)

        def on_changed(*args):
            self.refresh_fullname_label()
        for widget_name in ['sp_infra_rank_combo', 'sp_hybrid_combo',
                            'sp_spqual_combo']:
            w = self.view.widgets[widget_name]
            self.view.connect_after(widget_name, 'changed', on_changed)


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
        self.view.disconnect_all()
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
        self.refresh_sensitivity()
        self.vern_presenter.refresh_view(self.model.default_vernacular_name)
        self.synonyms_presenter.refresh_view()
        self.dist_presenter.refresh_view()



class DistributionPresenter(editor.GenericEditorPresenter):
    """
    """

    def __init__(self, species, view, session):
        '''
        @param species:
        @param view:
        @param session:
        '''
        super(DistributionPresenter, self).__init__(species, view)
        self.session = session
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


    def on_activate_add_menu_item(self, widget, id=None):
        from bauble.plugins.plants.species_model import Geography
        geo = self.session.query(Geography).filter_by(id=id).one()
        # check that this geography isn't already in the distributions
        if geo in [d.geography for d in self.model.distribution]:
#            debug('%s already in %s' % (geo, self.model))
            return
        dist = SpeciesDistribution(geography=geo)
        self.model.distribution.append(dist)
#        debug([str(d) for d in self.model.distribution])
        self.__dirty = True
        self.refresh_view()
        self.view.set_accept_buttons_sensitive(True)


    def on_activate_remove_menu_item(self, widget, dist):
        self.model.distribution.remove(dist)
        utils.delete_or_expunge(dist)
        self.refresh_view()
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(True)


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
        # hash is being build
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

        def build_menu(id, name):
            item = gtk.MenuItem(name)
            if not has_kids(id):
                if item.get_submenu() is None:
                    self.view.connect(item, 'activate',
                                      self.on_activate_add_menu_item,id)
                return item

            kids_added = False
            submenu = gtk.Menu()
            # removes two levels of kids with the same name, there must be a
            # better way to do this but i got tired of thinking about it
            for kid_id, kid_name in get_kids(id):
                if kid_name == name:
                    for gk_id, gk_name in get_kids(kid_id):
                        if gk_name == kid_name:
                            for gk2_id, gk2_name in get_kids(gk_id):
                                submenu.append(build_menu(gk2_id, gk2_name))
                                kids_added = True
                        else:
                            submenu.append(build_menu(gk_id, gk_name))
                            kids_added = True
                else:
                    submenu.append(build_menu(kid_id, kid_name))
                    kids_added = True

            if kids_added:
                sel_item = gtk.MenuItem(name)
                submenu.insert(sel_item, 0)
                submenu.insert(gtk.SeparatorMenuItem(), 1)
                item.set_submenu(submenu)
                self.view.connect(sel_item, 'activate',
                                  self.on_activate_add_menu_item,id)
            else:
                self.view.connect(item, 'activate',
                                  self.on_activate_add_menu_item, id)
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
    def __init__(self, species, view, session):
        '''
        @param model: a list of VernacularName objects
        @param view:
        @param session:
        '''
        super(VernacularNamePresenter, self).__init__(species, view)
        self.session = session
        self.__dirty = False
        self.init_treeview(species.vernacular_names)
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
        cell = column.get_cell_renderers()[0]
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
        self.view.set_accept_buttons_sensitive(True)
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
        self.view.set_accept_buttons_sensitive(True)


    def on_cell_edited(self, cell, path, new_text, prop):
        treemodel = self.treeview.get_model()
        vn = treemodel[path][0]
        if getattr(vn, prop) == new_text:
            return  # didn't change
        setattr(vn, prop, utils.utf8(new_text))
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(True)


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
            self.view.set_accept_buttons_sensitive(True)
        elif default_vernacular_name is None:
            return



class SynonymsPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1

    def __init__(self, model, view, session):
        '''
        @param model: a Species instance
        @param view: see GenericEditorPresenter
        @param session:
        '''
        super(SynonymsPresenter, self).__init__(model, view)
        self.session = session
        self.init_treeview()

        # use completions_model as a dummy object for completions, we'll create
        # seperate SpeciesSynonym models on add
        completions_model = SpeciesSynonym()
        def sp_get_completions(text):
            query = self.session.query(Species)
            query = query.join('genus')
            query = query.filter(utils.ilike(Genus.genus, '%s%%' % text))
            query = query.filter(Species.id != self.model.id)
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
        # remove any columns that were setup previous, this became a
        # problem when we starting reusing the glade files with
        # utils.GladeLoader, the right way to do this would be to
        # create the columns in glade instead of here
        for col in self.treeview.get_columns():
            self.treeview.remove_column(col)

        def _syn_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            #cell.set_property('text', str(v.synonym))
            cell.set_property('text', str(v))
            # just added so change the background color to indicate its new
            if v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)

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
        self.view.set_accept_buttons_sensitive(True)
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
            self.view.set_accept_buttons_sensitive(True)
            self.__dirty = True



class SpeciesEditorView(editor.GenericEditorView):

    expanders_pref_map = {}#'sp_infra_expander': 'editor.species.infra.expanded',
                          #}#'sp_meta_expander': 'editor.species.meta.expanded'}

    _tooltips = {
        'sp_genus_entry': _('Genus '),
        'sp_species_entry': _('Species epithet'),
        'sp_author_entry': _('Species author'),
        'sp_infra_rank_combo': _('Infraspecific rank'),
        'sp_hybrid_combo': _('Species hybrid flag'),
        'sp_infra_entry': _('Infraspecific epithet'),
        'sp_cvgroup_entry': _('Cultivar group'),
        'sp_infra_author_entry': _('Infraspecific author'),
        'sp_spqual_combo': _('Species qualifier'),
        'sp_notes_frame': _('Note'),
        'sp_dist_box': _('Species distribution'),
        'sp_vern_box': _('Vernacular names'),
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

    label = 'Species'
    mnemonic_label = '_Species'

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
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') % \
                        utils.xml_safe_utf8(e)
                debug(traceback.format_exc())
                #warning(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        more_committed = None
        if response == self.RESPONSE_NEXT:
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

        if self.model.sp_hybrid is None and self.model.infrasp_rank is None:
            self.model.infrasp = None
            self.model.infrasp_author = None
            self.model.cv_group = None

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
