# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2015 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# Species table definition
#


from gi.repository import Gtk
from gi.repository import GObject

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

import os
import traceback
import weakref

from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError

import bauble

from bauble.prefs import prefs
import bauble.utils as utils
import bauble.paths as paths
import bauble.editor as editor
from bauble.plugins.plants.geography import GeographicAreaMenu
from bauble.plugins.plants.family import Family
from bauble.plugins.plants.genus import Genus, GenusSynonym
from bauble.plugins.plants.species_model import (
    Species, SpeciesDistribution, VernacularName, SpeciesSynonym, Habit,
    infrasp_rank_values, compare_rank)


class SpeciesEditorPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_GENUS = 1

    widget_to_field_map = {'sp_genus_entry': 'genus',
                           'sp_species_entry': 'sp',
                           'sp_author_entry': 'sp_author',
                           'sp_hybrid_check': 'hybrid',
                           'sp_cvgroup_entry': 'cv_group',
                           'sp_spqual_combo': 'sp_qual',
                           'sp_awards_entry': 'awards',
                           'sp_label_dist_entry': 'label_distribution',
                           'sp_habit_comboentry': 'habit',
                           }

    def __init__(self, model, view):
        super().__init__(model, view)
        self.create_toolbar()
        self.session = object_session(model)
        self._dirty = False
        self.omonym_box = None
        self.species_check_messages = []
        self.genus_check_messages = []
        self.species_space = False  # do not accept spaces in epithet
        self.init_fullname_widgets()
        self.vern_presenter = VernacularNamePresenter(self)
        self.synonyms_presenter = SynonymsPresenter(self)
        self.dist_presenter = DistributionPresenter(self)
        self.infrasp_presenter = InfraspPresenter(self)

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = editor.NotesPresenter(
            self, 'notes', notes_parent)

        pictures_parent = self.view.widgets.pictures_parent_box
        pictures_parent.foreach(pictures_parent.remove)
        self.pictures_presenter = editor.PicturesPresenter(
            self, 'notes', pictures_parent)

        self.init_enum_combo('sp_spqual_combo', 'sp_qual')

        def cell_data_func(column, cell, model, treeiter, data=None):
            cell.props.text = utils.utf8(model[treeiter][0])

        combo = self.view.widgets.sp_habit_comboentry
        model = Gtk.ListStore(str, object)
        list(map(lambda p: model.append(p),
            [(str(h), h) for h in self.session.query(Habit)]))
        utils.setup_text_combobox(combo, model)

        def on_focus_out(entry, event):
            # check if the combo has a problem then check if the value
            # in the entry matches one of the habit codes and if so
            # then change the value to the habit
            code = entry.props.text
            try:
                utils.set_combo_from_value(
                    combo, code.lower(),
                    cmp=lambda r, v: str(r[1].code).lower() == v)
            except ValueError:
                pass
        combo.get_child().connect('focus-out-event', on_focus_out)

        # set the model values in the widgets
        self.refresh_view()

        # connect habit comboentry widget and child entry
        self.view.connect('sp_habit_comboentry', 'changed',
                          self.on_habit_comboentry_changed)

        # connect signals
        def gen_get_completions(text):
            clause = utils.ilike(Genus.genus, '%s%%' % str(text))
            return self.session.query(Genus).filter(clause).\
                order_by(Genus.genus)

        def sp_species_TPL_callback(found, accepted):
            # both found and accepted are dictionaries, their keys here
            # relevant: 'Species hybrid marker', 'Species', 'Authorship',
            # 'Taxonomic status in TPL'.

            # we can provide the user the option to accept spellings
            # corrections in 'Species', the full value of 'Authorship', and
            # full acceptedy links. it's TWO boxes that we might show. or
            # one if nothing matches.

            self.view.close_boxes()
            if found:
                found = dict((k, utils.to_unicode(v))
                             for k, v in list(found.items()))
                found_s = dict((k, utils.xml_safe(utils.to_unicode(v)))
                               for k, v in list(found.items()))
            if accepted:
                accepted = dict((k, utils.to_unicode(v))
                                for k, v in list(accepted.items()))
                accepted_s = dict((k, utils.xml_safe(utils.to_unicode(v)))
                                  for k, v in list(accepted.items()))

            msg_box_msg = _('No match found on ThePlantList.org')

            if not (found is None and accepted is None):

                # if inserted data matches found, just say so.
                if (self.model.sp == found['Species'] and
                        self.model.sp_author == found['Authorship'] and
                        self.model.hybrid == (
                            found['Species hybrid marker'] == '×')):
                    msg_box_msg = _(
                        'your data finely matches ThePlantList.org')
                else:
                    cit = ('<i>%(Genus)s</i> %(Species hybrid marker)s'
                           '<i>%(Species)s</i> %(Authorship)s (%(Family)s)'
                           ) % found_s
                    msg = _('%s is the closest match for your data.\n'
                            'Do you want to accept it?') % cit
                    b1 = box = self.view.add_message_box(
                        utils.MESSAGE_BOX_YESNO)
                    box.message = msg

                    def on_response_found(button, response):
                        self.view.remove_box(b1)
                        if response:
                            self.set_model_attr('sp', found['Species'])
                            self.set_model_attr('sp_author', found['Authorship'])
                            self.set_model_attr(
                                'hybrid',
                                found['Species hybrid marker'] == '×')
                            self.refresh_view()
                            self.refresh_fullname_label()
                    box.on_response = on_response_found
                    box.show()
                    self.view.add_box(box)
                    self.species_check_messages.append(box)
                    msg_box_msg = None

                if self.model.accepted is None and accepted is not None:
                    if not accepted:  # infraspecific synonym, can't handle
                        msg = _('closest match is a synonym of something at '
                                'infraspecific rank, which I cannot handle.')
                        b2 = box = self.view.add_message_box(
                            utils.MESSAGE_BOX_INFO)
                        box.message = msg

                        def on_response_accepted(button, response):
                            self.view.remove_box(b2)
                    else:
                        ## synonym is at rank species, this is fine
                        cit = ('<i>%(Genus)s</i> %(Species hybrid marker)s'
                               '<i>%(Species)s</i> %(Authorship)s (%(Family)s)'
                              ) % accepted_s
                        msg = _('%s is the accepted taxon for your data.\n'
                                'Do you want to add it?') % cit
                        b2 = box = self.view.add_message_box(
                            utils.MESSAGE_BOX_YESNO)
                        box.message = msg

                        def on_response_accepted(button, response):
                            self.view.remove_box(b2)
                            if response:
                                hybrid = accepted['Species hybrid marker'] == Species.hybrid_char
                                self.model.accepted = Species.retrieve_or_create(
                                    self.session, {
                                        'object': 'taxon',
                                        'rank': 'species',
                                        'ht-rank': 'genus',
                                        'familia': accepted['Family'],
                                        'ht-epithet': accepted['Genus'],
                                        'epithet': accepted['Species'],
                                        'author': accepted['Authorship'],
                                        'hybrid': hybrid}
                                    )
                                self.refresh_view()
                                self.refresh_fullname_label()

                    box.on_response = on_response_accepted
                    box.show()
                    self.view.add_box(box)
                    self.species_check_messages.append(box)
                    msg_box_msg = None

            if msg_box_msg is not None:
                b0 = self.view.add_message_box(utils.MESSAGE_BOX_INFO)
                b0.message = msg_box_msg
                b0.on_response = lambda b, r: self.view.remove_box(b0)
                b0.show()
                self.view.add_box(b0)
                self.species_check_messages.append(b0)

        def on_sp_species_button_clicked(widget, event=None):
            # the real activity runs in a separate thread.
            from .ask_tpl import AskTPL

            while self.species_check_messages:
                kid = self.species_check_messages.pop()
                self.view.widgets.remove_parent(kid)

            binomial = '%s %s' % (self.model.genus, self.model.sp)
            AskTPL(binomial, sp_species_TPL_callback, timeout=2, gui=True
                   ).start()
            b0 = self.view.add_message_box(utils.MESSAGE_BOX_INFO)
            b0.message = _("querying the plant list")
            b0.on_response = lambda b, r: self.view.remove_box(b0)
            b0.show()
            self.view.add_box(b0)
            if event is not None:
                return False

        self.view.connect('sp_species_button', "clicked",
                          on_sp_species_button_clicked)

        # called when a genus is selected from the genus completions
        def on_select(value):
            logger.debug('on select: %s' % value)
            if isinstance(value, str):
                value = self.session.query(Genus).filter(
                    Genus.genus == value).first()
            while self.genus_check_messages:
                kid = self.genus_check_messages.pop()
                self.view.widgets.remove_parent(kid)
            self.set_model_attr('genus', value)
            if not value:  # no choice is a fine choice
                return
            ## is value considered a synonym?
            syn = self.session.query(GenusSynonym).filter(
                GenusSynonym.synonym_id == value.id).first()
            if not syn:
                # chosen value is not a synonym, also fine
                return

            ## value is a synonym: user alert needed
            msg = _('The genus <b>%(synonym)s</b> is a synonym of '
                    '<b>%(genus)s</b>.\n\nWould you like to choose '
                    '<b>%(genus)s</b> instead?') % \
                {'synonym': syn.synonym, 'genus': syn.genus}
            box = None

            def on_response(button, response):
                self.view.remove_box(box)
                if response:
                    self.set_model_attr('genus', syn.genus)
                    self.refresh_view()
                    self.refresh_fullname_label()
            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()
            self.view.add_box(box)
            self.genus_check_messages.append(box)

        on_select(self.model.genus)

        self.assign_completions_handler('sp_genus_entry',  # 'genus',
                                        gen_get_completions,
                                        on_select=on_select)
        self.assign_simple_handler('sp_cvgroup_entry', 'cv_group',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_spqual_combo', 'sp_qual',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_label_dist_entry', 'label_distribution',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('sp_awards_entry', 'awards',
                                   editor.UnicodeOrNoneValidator())

        try:
            import bauble.plugins.garden
            bauble.plugins.garden  # fake its usage
            if self.model not in self.model.new:
                self.view.widgets.sp_ok_and_add_button.set_sensitive(True)
        except Exception:
            pass

    def set_visible_buttons(self, visible):
        self.view.widgets.sp_ok_and_add_button.set_visible(visible)
        self.view.widgets.sp_next_button.set_visible(visible)

    def on_sp_species_entry_changed(self, widget, *args):
        self.on_text_entry_changed(widget, *args)
        self.on_entry_changed_clear_boxes(widget, *args)

    def on_entry_changed_clear_boxes(self, widget, *args):
        while self.species_check_messages:
            kid = self.species_check_messages.pop()
            self.view.widgets.remove_parent(kid)

    def on_habit_comboentry_changed(self, combo, *args):
        """
        Changed handler for sp_habit_comboentry.

        We don't need specific handlers for either comboentry because
        the validation is done in the specific Gtk.Entry handlers for
        the child of the combo entries.
        """
        treeiter = combo.get_active_iter()
        if not treeiter:
            return
        value = combo.get_model()[treeiter][1]
        self.set_model_attr('habit', value)
        # the entry change handler does the validation of the model
        combo.get_child().props.text = utils.utf8(value)
        combo.get_child().set_position(-1)

    def __del__(self):
        # we have to delete the views in the child presenters manually
        # to avoid the circular reference
        del self.vern_presenter.view
        del self.synonyms_presenter.view
        del self.dist_presenter.view
        del self.notes_presenter.view
        del self.infrasp_presenter.view

    def is_dirty(self):
        return (self._dirty or
                self.pictures_presenter.is_dirty() or
                self.vern_presenter.is_dirty() or
                self.synonyms_presenter.is_dirty() or
                self.dist_presenter.is_dirty() or
                self.infrasp_presenter.is_dirty() or
                self.notes_presenter.is_dirty())

    def set_model_attr(self, field, value, validator=None):
        '''
        Resets the sensitivity on the ok buttons and the name widgets
        when values change in the model
        '''
        super().set_model_attr(field, value,
                                                           validator)
        self._dirty = True
        sensitive = True
        if len(self.problems) != 0 \
           or len(self.vern_presenter.problems) != 0 \
           or len(self.synonyms_presenter.problems) != 0 \
           or len(self.dist_presenter.problems) != 0:
            sensitive = False
        elif not self.model.genus:
            sensitive = False
        # elif not (self.model.sp or self.model.cv_group or \
        #         (self.model.infrasp_rank == 'cv.' and self.model.infrasp)):
        #     sensitive = False
        self.view.set_accept_buttons_sensitive(sensitive)

    def refresh_sensitivity(self):
        """
        :param self:
        """
        self.view.set_accept_buttons_sensitive(self.is_dirty())

    def init_fullname_widgets(self):
        '''
        initialized the signal handlers on the widgets that are relative to
        building the fullname string in the sp_fullname_label widget
        '''
        self.refresh_fullname_label()
        refresh = lambda *args: self.refresh_fullname_label(*args)
        widgets = ['sp_genus_entry', 'sp_species_entry', 'sp_author_entry',
                   'sp_cvgroup_entry', 'sp_spqual_combo']
        for widget_name in widgets:
            self.view.connect_after(widget_name, 'changed', refresh)
        self.view.connect_after('sp_hybrid_check', 'toggled', refresh)

    def on_sp_species_entry_insert_text(self, entry, text, length, position):
        '''remove all spaces from epithet
        '''

        while self.species_check_messages:
            kid = self.species_check_messages.pop()
            self.view.widgets.remove_parent(kid)

        # get position from entry, can't trust position parameter
        position = entry.get_position()
        if text.count('×'):
            self.species_space = True
        if text.count('*'):
            self.species_space = True
            text = text.replace('*', " × ")
        if self.species_space is False:
            text = text.replace(' ', '')
        if text != '':
            # Insert the text at cursor (block handler to avoid recursion).
            entry.handler_block_by_func(self.on_sp_species_entry_insert_text)
            entry.insert_text(text, position)
            entry.handler_unblock_by_func(self.on_sp_species_entry_insert_text)
            # Set the new cursor position immediately after the inserted text.
            new_pos = position + len(text)
            # Can't modify the cursor position from within this handler,
            # so we add it to be done at the end of the main loop:
            GObject.idle_add(entry.set_position, new_pos)

        # We handled the signal so stop it from being processed further.
        entry.stop_emission("insert_text")

    def refresh_fullname_label(self, widget=None):
        '''
        set the value of sp_fullname_label to either '--' if there
        is a problem or to the name of the string returned by Species.str
        '''
        logger.debug("SpeciesEditorPresenter:refresh_fullname_label %s"
                     % widget)
        if len(self.problems) > 0 or self.model.genus is None:
            self.view.set_label('sp_fullname_label', '--')
            return
        sp_str = self.model.str(markup=True, authors=True)
        self.view.set_label('sp_fullname_label', sp_str)
        if self.model.genus is not None:
            genus = self.model.genus
            epithet = self.view.widget_get_value('sp_species_entry')
            omonym = self.session.query(
                Species).filter(
                Species.genus == genus,
                Species.sp == epithet
                ).first()
            logger.debug("looking for %s %s, found %s"
                         % (genus, epithet, omonym))
            if omonym in [None, self.model]:
                ## should not warn, so check warning and remove
                if self.omonym_box is not None:
                    self.view.remove_box(self.omonym_box)
                    self.omonym_box = None
            elif self.omonym_box is None:  # should warn, but not twice
                msg = _("This binomial name is already in your collection"
                        ", as %s.\n\n"
                        "Are you sure you want to insert it again?") % \
                    omonym.str(authors=True, markup=True)

                def on_response(button, response):
                    self.view.remove_box(self.omonym_box)
                    self.omonym_box = None
                    if response:
                        logger.warning('yes')
                    else:
                        self.view.widget_set_value('sp_species_entry', '')

                box = self.omonym_box = (
                    self.view.add_message_box(utils.MESSAGE_BOX_YESNO))
                box.message = msg
                box.on_response = on_response
                box.show()
                self.view.add_box(box)

    def cleanup(self):
        super().cleanup()
        self.vern_presenter.cleanup()
        self.synonyms_presenter.cleanup()
        self.dist_presenter.cleanup()
        self.infrasp_presenter.cleanup()

    def start(self):
        r = self.view.start()
        return r

    def refresh_view(self):
        for widget, field in self.widget_to_field_map.items():
            if field is 'genus_id':
                value = self.model.genus
            else:
                value = getattr(self.model, field)
            logger.debug('%s, %s, %s(%s)'
                         % (widget, field, type(value), value))
            self.view.widget_set_value(widget, value)

        utils.set_widget_value(self.view.widgets.sp_habit_comboentry,
                               self.model.habit or '')
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
        super().__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self._dirty = False
        self.view.connect('add_infrasp_button', "clicked", self.append_infrasp)

        # will table.resize() remove the children??
        table = self.view.widgets.infrasp_table
        for item in self.view.widgets.infrasp_table.get_children():
            if not isinstance(item, Gtk.Label):
                self.view.widgets.remove_parent(item)

        self.table_rows = []
        for index in range(1, 5):
            infrasp = self.model.get_infrasp(index)
            if infrasp != (None, None, None):
                self.append_infrasp()

    def is_dirty(self):
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
            self.rank_combo = Gtk.ComboBox()
            self.presenter.view.init_translatable_combo(
                self.rank_combo, infrasp_rank_values, cmp=compare_rank)
            utils.set_widget_value(self.rank_combo, rank)
            presenter.view.connect(self.rank_combo,
                                   'changed', self.on_rank_combo_changed)
            table.attach(self.rank_combo, 0, 1, level, level+1,
                         xoptions=Gtk.AttachOptions.FILL, yoptions=-1)

            # epithet entry
            self.epithet_entry = Gtk.Entry()
            utils.set_widget_value(self.epithet_entry, epithet)
            presenter.view.connect(self.epithet_entry, 'changed',
                                   self.on_epithet_entry_changed)
            table.attach(self.epithet_entry, 1, 2, level, level+1,
                         xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND, yoptions=-1)

            # author entry
            self.author_entry = Gtk.Entry()
            utils.set_widget_value(self.author_entry, author)
            presenter.view.connect(self.author_entry, 'changed',
                                   self.on_author_entry_changed)
            table.attach(self.author_entry, 2, 3, level, level+1,
                         xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND, yoptions=-1)

            self.remove_button = Gtk.Button()
            img = Gtk.Image.new_from_stock(Gtk.STOCK_REMOVE,
                                           Gtk.IconSize.BUTTON)
            self.remove_button.props.image = img
            presenter.view.connect(self.remove_button, 'clicked',
                                   self.on_remove_button_clicked)
            table.attach(self.remove_button, 3, 4, level, level+1,
                         xoptions=Gtk.AttachOptions.FILL, yoptions=-1)
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
            self.presenter._dirty = True
            self.presenter.parent_ref().refresh_fullname_label()
            self.presenter.parent_ref().refresh_sensitivity()

        def on_rank_combo_changed(self, combo, *args):
            logger.info("on_rank_combo_changed(%s, %s)" % (combo, args))
            model = combo.get_model()
            it = combo.get_active_iter()
            value = model[it][0]
            if value is not None:
                self.set_model_attr('rank', utils.utf8(model[it][0]))
            else:
                self.set_model_attr('rank', None)

        def on_epithet_entry_changed(self, entry, *args):
            logger.info("on_epithet_entry_changed(%s, %s)" % (entry, args))
            value = utils.utf8(entry.props.text)
            if not value:  # if None or ''
                value = None
            self.set_model_attr('epithet', value)
            ## now warn if same binomial is already in database

        def on_author_entry_changed(self, entry, *args):
            logger.info("on_author_entry_changed(%s, %s)" % (entry, args))
            value = utils.utf8(entry.props.text)
            if not value:  # if None or ''
                value = None
            self.set_model_attr('author', value)


class DistributionPresenter(editor.GenericEditorPresenter):
    """
    """

    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super().__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self._dirty = False
        self.remove_menu = Gtk.Menu()
        self.remove_menu.attach_to_widget(
            self.view.widgets.sp_dist_remove_button, None)
        self.view.connect('sp_dist_add_button', 'button-press-event',
                          self.on_add_button_pressed)
        self.view.connect('sp_dist_remove_button', 'button-press-event',
                          self.on_remove_button_pressed)
        self.view.widgets.sp_dist_add_button.set_sensitive(False)

        def _init_geo():
            add_button = self.view.widgets.sp_dist_add_button
            self.geo_menu = GeographicAreaMenu(self.on_activate_add_menu_item)
            self.geo_menu.attach_to_widget(add_button, None)
            add_button.set_sensitive(True)
        GObject.idle_add(_init_geo)

    def refresh_view(self):
        label = self.view.widgets.sp_dist_label
        s = ', '.join([str(d) for d in self.model.distribution])
        label.set_text(s)

    def on_add_button_pressed(self, button, event):
        self.geo_menu.popup(None, None, None, event.button, event.time)

    def on_remove_button_pressed(self, button, event):
        # clear the menu
        for c in self.remove_menu.get_children():
            self.remove_menu.remove(c)
        # add distributions to menu
        for dist in self.model.distribution:
            item = Gtk.MenuItem(str(dist))
            self.view.connect(item, 'activate',
                              self.on_activate_remove_menu_item, dist)
            self.remove_menu.append(item)
        self.remove_menu.show_all()
        self.remove_menu.popup(None, None, None, event.button, event.time)

    def on_activate_add_menu_item(self, widget, geoid=None):
        logger.debug('on_activate_add_menu_item %s %s' % (widget, geoid))
        from bauble.plugins.plants.geography import GeographicArea
        geo = self.session.query(GeographicArea).filter_by(id=geoid).one()
        # check that this geography isn't already in the distributions
        if geo in [d.geographic_area for d in self.model.distribution]:
            logger.debug('%s already in %s' % (geo, self.model))
            return
        dist = SpeciesDistribution(geographic_area=geo)
        self.model.distribution.append(dist)
        logger.debug([str(d) for d in self.model.distribution])
        self._dirty = True
        self.refresh_view()
        self.parent_ref().refresh_sensitivity()

    def on_activate_remove_menu_item(self, widget, dist):
        self.model.distribution.remove(dist)
        utils.delete_or_expunge(dist)
        self.refresh_view()
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def is_dirty(self):
        return self._dirty


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
        super(
              ).__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self._dirty = False
        self.init_treeview(self.model.vernacular_names)
        self.view.connect('sp_vern_add_button', 'clicked',
                          self.on_add_button_clicked)
        self.view.connect('sp_vern_remove_button', 'clicked',
                          self.on_remove_button_clicked)

    def is_dirty(self):
        """
        @return True or False if the vernacular names have changed.
        """
        return self._dirty

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

        msg = _('Are you sure you want to remove the vernacular '
                'name <b>%s</b>?') % utils.xml_safe(vn.name)
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
        self._dirty = True

    def on_default_toggled(self, cell, path, data=None):
        """
        Default column callback.
        """
        active = cell.get_active()
        if not active:  # then it's becoming active
            vn = self.treeview.get_model()[path][0]
            self.set_model_attr('default_vernacular_name', vn)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_cell_edited(self, cell, path, new_text, prop):
        treemodel = self.treeview.get_model()
        vn = treemodel[path][0]
        if getattr(vn, prop) == new_text:
            return  # didn't change
        setattr(vn, prop, utils.utf8(new_text))
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def init_treeview(self, model):
        """
        Initialized the list of vernacular names.

        The columns and cell renderers are loaded from the .glade file
        so we just need to customize them a bit.
        """
        self.treeview = self.view.widgets.vern_treeview
        if not isinstance(self.treeview, Gtk.TreeView):
            return

        def _name_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', v.name)
            # just added so change the background color to indicate it's new
            if v.id is None:  # hasn't been committed
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        column = self.view.widgets.vn_name_column
        #column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        cell = self.view.widgets.vn_name_cell
        self.view.widgets.vn_name_column.\
            set_cell_data_func(cell, _name_data_func)
        self.view.connect(cell, 'edited', self.on_cell_edited, 'name')

        def _lang_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', v.language)
            # just added so change the background color to indicate it's new
            #if not v.isinstance:`
            if v.id is None:  # hasn't been committed
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
                cell.set_property(
                    'active', v == self.model.default_vernacular_name)
                return
            except AttributeError as e:
                logger.debug("AttributeError %s" % e)
                pass
            cell.set_property('active', False)

        cell = self.view.widgets.vn_default_cell
        self.view.widgets.vn_default_column.\
            set_cell_data_func(cell, _default_data_func)
        self.view.connect(cell, 'toggled', self.on_default_toggled)

        utils.clear_model(self.treeview)

        # add the vernacular names to the tree
        tree_model = Gtk.ListStore(object)
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
            msg = _('This species has vernacular names but none of them are '
                    'selected as the default. The first vernacular name in '
                    'the list has been automatically selected.')
            utils.message_dialog(msg)
            first = tree_model.get_iter_first()
            value = tree_model[first][0]
            path = tree_model.get_path(first)
            #self.set_model_attr('default_vernacular_name', value)
            self.model.default_vernacular_name = value
            self._dirty = True
            self.parent_ref().refresh_sensitivity()
        elif default_vernacular_name is None:
            return


class SynonymsPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1

    def __init__(self, parent):
        '''
        :param parent: the parent SpeciesEditorPresenter
        '''
        super().__init__(parent.model, parent.view)
        self.parent_ref = weakref.ref(parent)
        self.session = parent.session
        self.view.widgets.sp_syn_entry.props.text = ''
        self.init_treeview()

        def sp_get_completions(text):
            query = self.session.query(Species).join('genus').\
                filter(utils.ilike(Genus.genus, '%s%%' % text)).\
                filter(Species.id != self.model.id).\
                order_by(Genus.genus, Species.sp)
            return query

        def on_select(value):
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.sp_syn_add_button.set_sensitive(sensitive)
            self._selected = value
        self.assign_completions_handler('sp_syn_entry', sp_get_completions,
                                        on_select=on_select)
        on_select(None)  # set to default state

        self._selected = None
        self.view.connect('sp_syn_add_button', 'clicked',
                          self.on_add_button_clicked)
        self.view.connect('sp_syn_remove_button', 'clicked',
                          self.on_remove_button_clicked)
        self._dirty = False

    def is_dirty(self):
        return self._dirty

    def init_treeview(self):
        '''
        initialize the Gtk.TreeView
        '''
        self.treeview = self.view.widgets.sp_syn_treeview

        def _syn_data_func(column, cell, model, treeiter, data=None):
            v = model[treeiter][0]
            cell.set_property('text', str(v))
            # just added so change the background color to indicate it's new
            if not hasattr(v, 'id') or v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)

        col = self.view.widgets.syn_column
        col.set_cell_data_func(self.view.widgets.syn_cell, _syn_data_func)

        utils.clear_model(self.treeview)
        tree_model = Gtk.ListStore(object)
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
        Adds the synonym from the synonym entry to the list of synonyms for
        this species.
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
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

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
        s = value.synonym.str(markup=True)
        msg = 'Are you sure you want to remove %s as a synonym to the ' \
              'current species?\n\n<i>Note: This will not remove the species '\
              '%s from the database.</i>' % (s, s)
        if not utils.yes_no_dialog(msg, parent=self.view.get_window()):
            return

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

        # tmp_session = db.Session()
        # tmp_value = tmp.session.merge(value)
        # tmp.session.commit()
        # tmp.session.close()
        # self.session.refresh(value)
        #self.session.flush([value])
        self._dirty = True
        self.parent_ref().refresh_sensitivity()


class SpeciesEditorView(editor.GenericEditorView):

    expanders_pref_map = {}
    #{'sp_infra_expander': 'editor.species.infra.expanded',
    # 'sp_meta_expander': 'editor.species.meta.expanded'}

    _tooltips = {
        'sp_genus_entry': _('Genus'),
        'sp_species_entry': _('Species epithet'),
        'sp_author_entry': _('Species author'),
        'sp_hybrid_check': _('Species hybrid flag'),
        'sp_cvgroup_entry': _('Cultivar group'),
        'sp_spqual_combo': _('Species qualifier'),
        'sp_dist_frame': _('Species distribution'),
        'sp_vern_frame': _('Vernacular names'),
        'sp_syn_frame': _('Species synonyms'),
        'sp_label_dist_entry': _('The distribution string that will be used '
                                 'on the label.  If this entry is blank then '
                                 'the species distribution will be used'),
        'sp_habit_comboentry': _('The habit of this species'),
        'sp_awards_entry': _('The awards this species have been given'),
        'sp_cancel_button': _('Cancel your changes'),
        'sp_ok_button': _('Save your changes'),
        'sp_ok_and_add_button': _('Save your changes and add an '
                                  'accession to this species'),
        'sp_next_button': _('Save your changes and add another '
                            'species ')
        }

    def __init__(self, parent=None):
        '''
        the constructor

        :param parent: the parent window
        '''
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'species_editor.glade')
        super().__init__(filename, parent=parent)
        self.attach_completion('sp_genus_entry',
                               self.genus_completion_cell_data_func,
                               match_func=self.genus_match_func)
        self.attach_completion('sp_syn_entry', self.syn_cell_data_func)
        self.set_accept_buttons_sensitive(False)
        self.widgets.notebook.set_current_page(0)
        self.restore_state()
        self.boxes = set()

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
            bauble.plugins.garden  # fake usage
            self.widgets.sp_ok_and_add_button.set_sensitive(sensitive)
        except Exception:
            pass
        self.widgets.sp_next_button.set_sensitive(sensitive)

    @staticmethod
    def genus_completion_cell_data_func(column, renderer, model, treeiter, data=None):
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
        for expander, pref in self.expanders_pref_map.items():
            prefs[pref] = self.widgets[expander].get_expanded()

    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        for expander, pref in self.expanders_pref_map.items():
            expanded = prefs.get(pref, True)
            self.widgets[expander].set_expanded(expanded)

    def start(self):
        '''
        starts the views, essentially calls run() on the main dialog
        '''
        return self.get_window().run()


class SpeciesEditorMenuItem(editor.GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model=None, parent=None, is_dependent_window=False):
        '''
        :param model: a species instance or None
        :param parent: the parent window or None
        '''
        if model is None:
            model = Species()
        super().__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = SpeciesEditorView(parent=self.parent)
        self.presenter = SpeciesEditorPresenter(self.model, view)
        self.presenter.set_visible_buttons(not is_dependent_window)

        ## I do not follow this: we have a MVP model, but also an extra
        ## 'Editor' thing and is it stealing functionality from either the
        ## view or the presenter?
        self.view = view

        # set default focus
        if self.model.genus is None:
            view.widgets.sp_genus_entry.grab_focus()
        else:
            view.widgets.sp_species_entry.grab_focus()

    def handle_response(self, response):
        """
        @return: return True if the editor is ready to be closed, False if
        we want to keep editing, if any changes are committed they are stored
        in self._committed
        """
        # TODO: need to do a __cleanup_model before the commit to do things
        # like remove the insfraspecific information that's attached to the
        # model if the infraspecific rank is None
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == Gtk.ResponseType.OK or response in self.ok_responses:
            try:
                if self.presenter.is_dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except DBAPIError as e:
                msg = _('Error committing changes.\n\n%s') % \
                    utils.xml_safe(e.orig)
                logger.debug(traceback.format_exc())
                utils.message_details_dialog(msg, str(e), Gtk.MessageType.ERROR)
                return False
            except Exception as e:
                msg = _('Unknown error when committing changes. See the '
                        'details for more information.\n\n%s') % \
                    utils.xml_safe(e)
                logger.debug(traceback.format_exc())
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             Gtk.MessageType.ERROR)
                return False
        elif self.presenter.is_dirty() and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.is_dirty():
            self.session.rollback()
            self.view.close_boxes()
            return True
        else:
            return False

        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = SpeciesEditorMenuItem(
                Species(genus=self.model.genus), self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            from bauble.plugins.garden.accession import (
                AccessionEditor, Accession)
            e = AccessionEditor(Accession(species=self.model),
                                parent=self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        self.view.close_boxes()
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
        super().commit_changes()

    def start(self):
        if self.session.query(Genus).count() == 0:
            msg = _('You must first add or import at least one genus into the '
                    'database before you can add species.')
            utils.message_dialog(msg)
            return

        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.presenter.cleanup()
        self.session.close()  # cleanup session
        return self._committed


def edit_species(model=None, parent_view=None, is_dependent_window=False):
    kkk = SpeciesEditorMenuItem(model, parent_view, is_dependent_window)
    kkk.start()
    result = kkk._committed
    del kkk
    return result
