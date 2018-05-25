# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
# Genera table module
#


import os
import traceback
import weakref
import xml

from gi.repository import Gtk

import logging
logger = logging.getLogger(__name__)

from sqlalchemy import (
    Column, Unicode, Integer, ForeignKey, UnicodeText, String,
    UniqueConstraint, func, and_)
from sqlalchemy.orm import relation, backref, validates, synonym
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.associationproxy import association_proxy


import bauble
import bauble.db as db
import bauble.error as error
import bauble.pluginmgr as pluginmgr
import bauble.editor as editor
import bauble.utils as utils
import bauble.btypes as types
import bauble.paths as paths
from bauble.prefs import prefs
from bauble.view import (InfoBox, InfoExpander, PropertiesExpander,
                         select_in_search_results, Action)
import bauble.view as view

# TODO: warn the user that a duplicate genus name is being entered
# even if only the author or qualifier is different

# TODO: since there can be more than one genus with the same name but
# different authors we need to show the Genus author in the result
# search, we should also check if when entering a plantname with a
# chosen genus if that genus has an author ask the user if they want
# to use the accepted name and show the author of the genus then so
# they aren't using the wrong version of the Genus, e.g. Cananga


def edit_callback(genera):
    genus = genera[0]
    return GenusEditor(model=genus).start() is not None


def add_species_callback(genera):
    session = db.Session()
    genus = session.merge(genera[0])
    from bauble.plugins.plants.species_editor import edit_species
    result = edit_species(model=Species(genus=genus)) is not None
    session.close()
    return result


def remove_callback(genera):
    """
    The callback function to remove a genus from the genus context menu.
    """
    genus = genera[0]
    from bauble.plugins.plants.species_model import Species
    session = object_session(genus)
    nsp = session.query(Species).filter_by(genus_id=genus.id).count()
    safe_str = utils.xml_safe(str(genus))
    if nsp > 0:
        msg = (_('The genus <i>%(1)s</i> has %(2)s species.'
                 '\n\n') % {'1': safe_str, '2': nsp} +
               _('You cannot remove a genus with species.'))
        utils.message_dialog(msg, type=Gtk.MessageType.WARNING)
        return
    else:
        msg = (_("Are you sure you want to remove the genus <i>%s</i>?")
               % safe_str)
    if not utils.yes_no_dialog(msg):
        return
    try:
        obj = session.query(Genus).get(genus.id)
        session.delete(obj)
        session.commit()
    except Exception as e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=Gtk.MessageType.ERROR)
    return True


edit_action = Action('genus_edit', _('_Edit'),
                     callback=edit_callback,
                     accelerator='<ctrl>e')
add_species_action = Action('genus_sp_add', _('_Add species'),
                            callback=add_species_callback,
                            accelerator='<ctrl>k')
remove_action = Action('genus_remove', _('_Delete'),
                       callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

genus_context_menu = [edit_action, add_species_action, remove_action]


class Genus(db.Base, db.Serializable, db.WithNotes):
    """
    :Table name: genus

    :Columns:
        *genus*:
            The name of the genus.  In addition to standard generic
            names any additional hybrid flags or genera should included here.

        *qualifier*:
            Designates the botanical status of the genus.

            Possible values:
                * s. lat.: aggregrate genus (sensu lato)

                * s. str.: segregate genus (sensu stricto)

        *author*:
            The name or abbreviation of the author who published this genus.

    :Properties:
        *family*:
            The family of the genus.

        *synonyms*:
            The list of genera who are synonymous with this genus.  If
            a genus is listed as a synonym of this genus then this
            genus should be considered the current and valid name for
            the synonym.

    :Contraints:
        The combination of genus, author, qualifier
        and family_id must be unique.
    """
    __tablename__ = 'genus'
    __table_args__ = (UniqueConstraint('genus', 'author',
                                       'qualifier', 'family_id'),
                      {})
    __mapper_args__ = {'order_by': ['genus', 'author']}

    rank = 'genus'
    link_keys = ['accepted']

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        return utils.xml_safe(self), utils.xml_safe(self.family)

    @property
    def cites(self):
        '''the cites status of this taxon, or None
        '''

        cites_notes = [i.note for i in self.notes
                       if i.category and i.category.upper() == 'CITES']
        if not cites_notes:
            return self.family.cites
        return cites_notes[0]

    @property
    def hybrid_epithet(self):
        '''strip the leading char if it is an hybrid marker
        '''
        if self.genus[0] in ['x', '×']:
            return self.genus[1:]
        if self.genus[0] in ['+', '➕']:
            return self.genus[1:]
        return self.genus

    @property
    def hybrid_marker(self):
        """Intergeneric Hybrid Flag (ITF2)
        """
        if self.genus[0] in ['x', '×']:
            return '×'
        if self.genus[0] in ['+', '➕']:
            return '+'
        if self.genus.find('×') > 0:
            # the genus field contains a formula
            return 'H'
        return ''

    # columns
    genus = Column(String(64), nullable=False, index=True)
    epithet = synonym('genus')

    # use '' instead of None so that the constraints will work propertly
    author = Column(Unicode(255), default='')

    @validates('genus', 'author')
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    qualifier = Column(types.Enum(values=['s. lat.', 's. str', '']),
                       default='')

    family_id = Column(Integer, ForeignKey('family.id'), nullable=False)

    # relations
    # `species` relation is defined outside of `Genus` class definition
    synonyms = association_proxy('_synonyms', 'synonym')
    _synonyms = relation('GenusSynonym',
                         primaryjoin='Genus.id==GenusSynonym.genus_id',
                         cascade='all, delete-orphan', uselist=True,
                         backref='genus')

    # this is a dummy relation, it is only here to make cascading work
    # correctly and to ensure that all synonyms related to this genus
    # get deleted if this genus gets deleted
    __syn = relation('GenusSynonym',
                     primaryjoin='Genus.id==GenusSynonym.synonym_id',
                     cascade='all, delete-orphan', uselist=True)

    @property
    def accepted(self):
        'Name that should be used if name of self should be rejected'
        session = object_session(self)
        if not session:
            logger.warn('genus:accepted - object not in session')
            return None
        syn = session.query(GenusSynonym).filter(
            GenusSynonym.synonym_id == self.id).first()
        accepted = syn and syn.genus
        return accepted

    @accepted.setter
    def accepted(self, value):
        'Name that should be used if name of self should be rejected'
        assert isinstance(value, self.__class__)
        if self in value.synonyms:
            return
        # remove any previous `accepted` link
        session = object_session(self)
        if not session:
            logger.warn('genus:accepted.setter - object not in session')
            return
        session.query(GenusSynonym).filter(
            GenusSynonym.synonym_id == self.id).delete()
        session.commit()
        value.synonyms.append(self)

    def __repr__(self):
        return Genus.str(self)

    @staticmethod
    def str(genus, author=False):
        # TODO: the genus should be italicized for markup
        if genus.genus is None:
            return repr(genus)
        elif not author or genus.author is None:
            return ' '.join([s for s in [genus.genus, genus.qualifier]
                             if s not in ('', None)])
        else:
            return ' '.join(
                [s for s in [genus.genus, genus.qualifier,
                             xml.sax.saxutils.escape(genus.author)]
                 if s not in ('', None)])

    def has_accessions(self):
        '''true if genus is linked to at least one accession
        '''

        return False

    def as_dict(self, recurse=True):
        result = db.Serializable.as_dict(self)
        del result['genus']
        del result['qualifier']
        result['object'] = 'taxon'
        result['rank'] = 'genus'
        result['epithet'] = self.genus
        result['ht-rank'] = 'familia'
        result['ht-epithet'] = self.family.family
        if recurse and self.accepted is not None:
            result['accepted'] = self.accepted.as_dict(recurse=False)
        return result

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return session.query(cls).filter(
                cls.genus == keys['epithet']).one()
        except:
            if 'author' not in keys:
                return None
        try:
            return session.query(cls).filter(
                cls.genus == keys['epithet'],
                cls.author == keys['author']).one()
        except:
            return None

    @classmethod
    def correct_field_names(cls, keys):
        for internal, exchange in [('genus', 'epithet'),
                                   ('family', 'ht-epithet')]:
            if exchange in keys:
                keys[internal] = keys[exchange]
                del keys[exchange]

    @classmethod
    def compute_serializable_fields(cls, session, keys):
        from .family import Family
        result = {'family': None}
        ## retrieve family object
        if keys.get('ht-epithet'):
            result['family'] = Family.retrieve_or_create(
                session, {'epithet': keys['ht-epithet']},
                create=True)
        if result['family'] is None:
            raise error.NoResultException()
        return result

    def top_level_count(self):
        accessions = [a for s in self.species for a in s.accessions]
        plants = [p for a in accessions for p in a.plants]
        return {(1, 'Genera'): set([self.id]),
                (2, 'Families'): set([self.family.id]),
                (3, 'Species'): len(self.species),
                (4, 'Accessions'): len(accessions),
                (5, 'Plantings'): len(plants),
                (6, 'Living plants'): sum(p.quantity for p in plants),
                (7, 'Locations'): set(p.location.id for p in plants),
                (8, 'Sources'): set([a.source.source_detail.id
                                     for a in accessions
                                     if a.source and a.source.source_detail])}


def compute_serializable_fields(cls, session, keys):
    result = {'genus': None}

    genus_dict = {'epithet': keys['genus']}
    result['genus'] = Genus.retrieve_or_create(
        session, genus_keys, create=False)

    return result

GenusNote = db.make_note_class('Genus', compute_serializable_fields)


class GenusSynonym(db.Base):
    """
    :Table name: genus_synonym
    """
    __tablename__ = 'genus_synonym'

    # columns
    genus_id = Column(Integer, ForeignKey('genus.id'), nullable=False)

    # a genus can only be a synonum of one other genus
    synonym_id = Column(Integer, ForeignKey('genus.id'), nullable=False,
                        unique=True)

    # relations
    synonym = relation('Genus', uselist=False,
                       primaryjoin='GenusSynonym.synonym_id==Genus.id')

    def __init__(self, synonym=None, **kwargs):
        # it is necessary that the first argument here be synonym for
        # the Genus.synonyms association_proxy to work
        self.synonym = synonym
        super().__init__(**kwargs)

    def __str__(self):
        return str(self.synonym)


# late bindings
from bauble.plugins.plants.family import Family, FamilySynonym
from bauble.plugins.plants.species_model import Species
from bauble.plugins.plants.species_editor import edit_species

# only now that we have `Species` can we define the sorted `species` in
# the `Genus` class.
Genus.species = relation('Species', cascade='all, delete-orphan',
                         order_by=[Species.sp],
                         backref=backref('genus', uselist=False))


class GenusEditorView(editor.GenericEditorView):

    syn_expanded_pref = 'editor.genus.synonyms.expanded'

    _tooltips = {
        'gen_family_entry': _('The family name'),
        'gen_genus_entry': _('The genus name'),
        'gen_author_entry': _('The name or abbreviation of the author that '
                              'published this genus'),
        'gen_syn_frame': _('A list of synonyms for this genus.\n\nTo add a '
                           'synonym enter a genus name and select one from '
                           'the list of completions.  Then click Add to add '
                           'it to the list of synonyms.'),
        'gen_cancel_button': _('Cancel your changes.'),
        'gen_ok_button': _('Save your changes.'),
        'gen_ok_and_add_button': _('Save your changes and add a '
                                   'species to this genus.'),
        'gen_next_button': _('Save your changes and add another '
                             'genus.')
    }

    def __init__(self, parent=None):

        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'genus_editor.glade')
        super().__init__(filename, parent=parent)
        self.attach_completion('gen_syn_entry', self.syn_cell_data_func)
        self.attach_completion('gen_family_entry')
        self.set_accept_buttons_sensitive(False)
        self.widgets.notebook.set_current_page(0)
        self.restore_state()

    def get_window(self):
        return self.widgets.genus_dialog

    @staticmethod
    def syn_cell_data_func(column, renderer, model, iter, data=None):
        '''
        '''
        v = model[iter][0]
        author = None
        if v.author is None:
            author = ''
        else:
            author = utils.xml_safe(str(v.author))
        renderer.set_property('markup', '<i>%s</i> %s (<small>%s</small>)'
                              % (Genus.str(v), author, Family.str(v.family)))

    def save_state(self):
        '''
        save the current state of the gui to the preferences
        '''
        # for expander, pref in self.expanders_pref_map.iteritems():
        #     prefs[pref] = self.widgets[expander].get_expanded()
        pass

    def restore_state(self):
        '''
        restore the state of the gui from the preferences
        '''
        # for expander, pref in self.expanders_pref_map.iteritems():
        #     expanded = prefs.get(pref, True)
        #     self.widgets[expander].set_expanded(expanded)
        pass

    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.gen_ok_button.set_sensitive(sensitive)
        self.widgets.gen_ok_and_add_button.set_sensitive(sensitive)
        self.widgets.gen_next_button.set_sensitive(sensitive)

    def start(self):
        return self.get_window().run()


class GenusEditorPresenter(editor.GenericEditorPresenter):

    widget_to_field_map = {'gen_family_entry': 'family',
                           'gen_genus_entry': 'genus',
                           'gen_author_entry': 'author'}

    def __init__(self, model, view):
        '''
        @model: should be an instance of class Genus
        @view: should be an instance of GenusEditorView
        '''
        super().__init__(model, view)
        self.create_toolbar()
        self.session = object_session(model)

        # initialize widgets
        self.synonyms_presenter = SynonymsPresenter(self)
        self.refresh_view()  # put model values in view

        # connect signals
        def fam_get_completions(text):
            query = self.session.query(Family)
            return query.filter(Family.family.like('%s%%' % text)).\
                order_by(Family.family)

        def on_select(value):
            for kid in self.view.widgets.message_box_parent.get_children():
                self.view.widgets.remove_parent(kid)
            self.set_model_attr('family', value)
            if not value:
                return
            syn = self.session.query(FamilySynonym).filter(
                FamilySynonym.synonym_id == value.id).first()
            if not syn:
                self.set_model_attr('family', value)
                return
            msg = _('The family <b>%(synonym)s</b> is a synonym of '
                    '<b>%(family)s</b>.\n\nWould you like to choose '
                    '<b>%(family)s</b> instead?') % \
                {'synonym': syn.synonym, 'family': syn.family}
            box = None

            def on_response(button, response):
                self.view.widgets.remove_parent(box)
                box.destroy()
                if response:
                    # populate the completions model on the entry so
                    # when we set the text it will match the
                    # completion and set the value
                    completion = self.view.widgets.gen_family_entry.\
                        get_completion()
                    utils.clear_model(completion)
                    model = Gtk.ListStore(object)
                    model.append([syn.family])
                    completion.set_model(model)
                    self.view.widgets.gen_family_entry.\
                        set_text(utils.utf8(syn.family))
                    # the family value should be set properly when the
                    # text is set on the entry but it doesn't hurt to
                    # duplicate it here
                    self.set_model_attr('family', syn.family)

            box = self.view.add_message_box(utils.MESSAGE_BOX_YESNO)
            box.message = msg
            box.on_response = on_response
            box.show()

        self.assign_completions_handler('gen_family_entry',
                                        fam_get_completions,
                                        on_select=on_select)
        self.assign_simple_handler('gen_genus_entry', 'genus',
                                   editor.UnicodeOrNoneValidator())
        self.assign_simple_handler('gen_author_entry', 'author',
                                   editor.UnicodeOrNoneValidator())

        notes_parent = self.view.widgets.notes_parent_box
        notes_parent.foreach(notes_parent.remove)
        self.notes_presenter = \
            editor.NotesPresenter(self, 'notes', notes_parent)

        if self.model not in self.session.new:
            self.view.widgets.gen_ok_and_add_button.set_sensitive(True)

        self._dirty = False

    def cleanup(self):
        super().cleanup()
        self.synonyms_presenter.cleanup()
        self.notes_presenter.cleanup()

    def refresh_sensitivity(self):
        # TODO: check widgets for problems
        sensitive = False
        if self.model.family and self.model.genus and self.model.family:
            sensitive = True
        self.view.set_accept_buttons_sensitive(sensitive)

    def set_model_attr(self, field, value, validator=None):
        super().set_model_attr(field, value,
                                                         validator)
        self._dirty = True
        self.refresh_sensitivity()

    def dirty(self):
        return (self._dirty or self.synonyms_presenter.dirty() or
                self.notes_presenter.dirty())

    def refresh_view(self):
        for widget, field in self.widget_to_field_map.items():
            if field == 'family_id':
                value = getattr(self.model, 'family')
            else:
                value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)

    def start(self):
        r = self.view.start()
        return r


class SynonymsPresenter(editor.GenericEditorPresenter):

    PROBLEM_INVALID_SYNONYM = 1

    def __init__(self, parent):
        '''
        :param parent: GenusEditorPreesnter
        '''
        self.parent_ref = weakref.ref(parent)
        super().__init__(self.parent_ref().model,
                                                self.parent_ref().view)
        self.session = self.parent_ref().session
        self.view.widgets.gen_syn_entry.props.text = ''
        self.init_treeview()

        def gen_get_completions(text):
            query = self.session.query(Genus)
            return query.filter(and_(Genus.genus.like('%s%%' % text),
                                     Genus.id != self.model.id)).\
                order_by(Genus.genus)

        self._selected = None

        def on_select(value):
            # don't set anything in the model, just set self.selected
            sensitive = True
            if value is None:
                sensitive = False
            self.view.widgets.gen_syn_add_button.set_sensitive(sensitive)
            self._selected = value

        self.assign_completions_handler('gen_syn_entry', gen_get_completions,
                                        on_select=on_select)

        self.view.connect('gen_syn_add_button', 'clicked',
                          self.on_add_button_clicked)
        self.view.connect('gen_syn_remove_button', 'clicked',
                          self.on_remove_button_clicked)
        self._dirty = False

    def start(self):
        raise Exception('genus.SynonymsPresenter cannot be started')

    def dirty(self):
        return self._dirty

    def init_treeview(self):
        '''
        initialize the Gtk.TreeView
        '''
        self.treeview = self.view.widgets.gen_syn_treeview
        # remove any columns that were setup previous, this became a
        # problem when we starting reusing the glade files with
        # utils.BuilderLoader, the right way to do this would be to
        # create the columns in glade instead of here
        for col in self.treeview.get_columns():
            self.treeview.remove_column(col)

        def _syn_data_func(column, cell, model, iter, data=None):
            v = model[iter][0]
            syn = v.synonym
            cell.set_property('markup', '<i>%s</i> %s (<small>%s</small>)'
                              % (Genus.str(syn),
                                 utils.xml_safe(str(syn.author)),
                                 Family.str(syn.family)))
            # set background color to indicate it's new
            if v.id is None:
                cell.set_property('foreground', 'blue')
            else:
                cell.set_property('foreground', None)
        cell = Gtk.CellRendererText()
        col = Gtk.TreeViewColumn('Synonym', cell)
        col.set_cell_data_func(cell, _syn_data_func)
        self.treeview.append_column(col)

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
        self.view.widgets.gen_syn_remove_button.set_sensitive(True)

    def refresh_view(self):
        """
        doesn't do anything
        """
        return

    def on_add_button_clicked(self, button, data=None):
        '''
        adds the synonym from the synonym entry to the list of synonyms for
            this species
        '''
        syn = GenusSynonym(genus=self.model, synonym=self._selected)
        tree_model = self.treeview.get_model()
        tree_model.append([syn])
        self._selected = None
        entry = self.view.widgets.gen_syn_entry
        entry.props.text = ''
        entry.set_position(-1)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        self.view.widgets.gen_syn_add_button.set_sensitive(False)
        self._dirty = True
        self.parent_ref().refresh_sensitivity()

    def on_remove_button_clicked(self, button, data=None):
        '''
        removes the currently selected synonym from the list of synonyms for
        this species
        '''
        # TODO: maybe we should only ask 'are you sure' if the selected value
        # is an instance, this means it will be deleted from the database
        tree = self.view.widgets.gen_syn_treeview
        path, col = tree.get_cursor()
        tree_model = tree.get_model()
        value = tree_model[tree_model.get_iter(path)][0]
        s = Genus.str(value.synonym)
        msg = _('Are you sure you want to remove %(genus)s as a synonym to '
                'the current genus?\n\n<i>Note: This will not remove the '
                'genus from the database.</i>') % {'genus': s}
        if utils.yes_no_dialog(msg, parent=self.view.get_window()):
            tree_model.remove(tree_model.get_iter(path))
            self.model.synonyms.remove(value.synonym)
            utils.delete_or_expunge(value)
            self.session.flush([value])
            self._dirty = True
            self.refresh_sensitivity()


class GenusEditor(editor.GenericModelViewPresenterEditor):

    # these response values have to correspond to the response values in
    # the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model=None, parent=None):
        '''
        :param model: Genus instance or None
        :param parent: None
        '''
        # the view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Genus()
        super().__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = GenusEditorView(parent=self.parent)
        self.presenter = GenusEditorPresenter(self.model, view)

        # set default focus
        if self.model.family is None:
            view.widgets.gen_family_entry.grab_focus()
        else:
            view.widgets.gen_genus_entry.grab_focus()

    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == Gtk.ResponseType.OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except DBAPIError as e:
                msg = (_('Error committing changes.\n\n%s') %
                       utils.xml_safe(e.orig))
                utils.message_details_dialog(msg, str(e), Gtk.MessageType.ERROR)
                return False
            except Exception as e:
                msg = (_('Unknown error when committing changes. See the '
                         'details for more information.\n\n%s') %
                       utils.xml_safe(e))
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             Gtk.MessageType.ERROR)
                return False
        elif ((self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg))
              or not self.presenter.dirty()):
            self.session.rollback()
            return True
        else:
            # we should never really even get here since we would have
            # to hit something besides "OK" and the above elif should
            # handle all the possible cases
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            model = Genus(family=self.model.family)
            e = GenusEditor(model=model, parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            sp = Species(genus=self.model)
            more_committed = edit_species(model=sp, parent_view=self.parent)

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True

    def start(self):
        if self.session.query(Family).count() == 0:
            msg = _('You must first add or import at least one Family into '
                    'the database before you can add plants.')
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


from bauble.plugins.plants.species_model import Species

#
# InfoBox and InfoExpander
#


class GeneralGenusExpander(InfoExpander):
    '''
    expander to present general information about a genus
    '''

    def __init__(self, widgets):
        '''
        the constructor
        '''
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.gen_general_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box, True, True, 0)

        self.current_obj = None

        def on_family_clicked(*args):
            select_in_search_results(self.current_obj.family)
        utils.make_label_clickable(
            self.widgets.gen_fam_data, on_family_clicked)

        def on_nsp_clicked(*args):
            g = self.current_obj
            cmd = 'species where genus.genus="%s" and genus.qualifier="%s"' \
                % (g.genus, g.qualifier)
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.gen_nsp_data, on_nsp_clicked)

        def on_nacc_clicked(*args):
            g = self.current_obj
            cmd = 'accession where species.genus.genus="%s" ' \
                'and species.genus.qualifier="%s"' \
                % (g.genus, g.qualifier)
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.gen_nacc_data, on_nacc_clicked)

        def on_nplants_clicked(*args):
            g = self.current_obj
            cmd = 'plant where accession.species.genus.genus="%s" and ' \
                'accession.species.genus.qualifier="%s"' \
                % (g.genus, g.qualifier)
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(
            self.widgets.gen_nplants_data, on_nplants_clicked)

    def update(self, row):
        '''
        update the expander

        :param row: the row to get the values from
        '''
        session = object_session(row)
        self.current_obj = row
        self.widget_set_value('gen_name_data', '<big>%s</big> %s' %
                              (row, utils.xml_safe(str(row.author))),
                              markup=True)
        self.widget_set_value('gen_fam_data',
                              (utils.xml_safe(str(row.family))))

        # get the number of species
        nsp = (session.query(Species).
               join('genus').
               filter_by(id=row.id).count())
        self.widget_set_value('gen_nsp_data', nsp)

        # stop here if no GardenPlugin
        if 'GardenPlugin' not in pluginmgr.plugins:
            return

        from bauble.plugins.garden.accession import Accession
        from bauble.plugins.garden.plant import Plant

        # get number of accessions
        nacc = (session.query(Accession).
                join('species', 'genus').
                filter_by(id=row.id).count())
        if nacc == 0:
            self.widget_set_value('gen_nacc_data', nacc)
        else:
            nsp_in_acc = (session.query(Accession.species_id).
                          join('species', 'genus').
                          filter_by(id=row.id).distinct().count())
            self.widget_set_value('gen_nacc_data', '%s in %s species'
                                  % (nacc, nsp_in_acc))

        # get the number of plants in the genus
        nplants = (session.query(Plant).
                   join('accession', 'species', 'genus').
                   filter_by(id=row.id).count())
        if nplants == 0:
            self.widget_set_value('gen_nplants_data', nplants)
        else:
            nacc_in_plants = (session.query(Plant.accession_id).
                              join('accession', 'species', 'genus').
                              filter_by(id=row.id).distinct().count())
            self.widget_set_value('gen_nplants_data', '%s in %s accessions'
                                  % (nplants, nacc_in_plants))


class SynonymsExpander(InfoExpander):

    expanded_pref = 'infobox.genus.synonyms.expanded'

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Synonyms"), widgets)
        synonyms_box = self.widgets.gen_synonyms_box
        self.widgets.remove_parent(synonyms_box)
        self.vbox.pack_start(synonyms_box, True, True, 0)

    def update(self, row):
        '''
        update the expander

        :param row: the row to get the values from
        '''
        syn_box = self.widgets.gen_synonyms_box
        # remove old labels
        syn_box.foreach(syn_box.remove)
        # use True comparison in case the preference isn't set
        self.set_expanded(prefs[self.expanded_pref] is True)
        logger.debug("genus %s is synonym of %s and has synonyms %s" %
                     (row, row.accepted, row.synonyms))
        self.set_label(_("Synonyms"))  # reset default value
        if row.accepted is not None:
            self.set_label(_("Accepted name"))
            on_clicked = lambda l, e, syn: select_in_search_results(syn)
            # create clickable label that will select the synonym
            # in the search results
            box = Gtk.EventBox()
            label = Gtk.Label()
            label.set_alignment(0, .5)
            label.set_markup(Genus.str(row.accepted, author=True))
            box.add(label)
            utils.make_label_clickable(label, on_clicked, row.accepted)
            syn_box.pack_start(box, False, False, 0)
            self.show_all()
            self.set_sensitive(True)
        elif len(row.synonyms) == 0:
            self.set_sensitive(False)
        else:
            on_clicked = lambda l, e, syn: select_in_search_results(syn)
            for syn in row.synonyms:
                # create clickable label that will select the synonym
                # in the search results
                box = Gtk.EventBox()
                label = Gtk.Label()
                label.set_alignment(0, .5)
                label.set_markup(Genus.str(syn, author=True))
                box.add(label)
                utils.make_label_clickable(label, on_clicked, syn)
                syn_box.pack_start(box, False, False, 0)
            self.show_all()
            self.set_sensitive(True)


class GenusInfoBox(InfoBox):
    """
    """
    def __init__(self):
        button_defs = [
            {'name': 'GoogleButton', '_base_uri': "http://www.google.com/search?q=%s", '_space': '+', 'title': "Search Google", 'tooltip': None, },
            {'name': 'GBIFButton', '_base_uri': "http://www.gbif.org/species/search?q=%s", '_space': '+', 'title': _("Search GBIF"), 'tooltip': _("Search the Global Biodiversity Information Facility"), },
            {'name': 'ITISButton', '_base_uri': "http://www.itis.gov/servlet/SingleRpt/SingleRpt?search_topic=Scientific_Name&search_value=%s&search_kingdom=Plant&search_span=containing&categories=All&source=html&search_credRating=All", '_space': '%20', 'title': _("Search ITIS"), 'tooltip': _("Search the Intergrated Taxonomic Information System"), },
            {'name': 'GRINButton', '_base_uri': "http://www.ars-grin.gov/cgi-bin/npgs/swish/accboth?query=%s&submit=Submit+Text+Query&si=0", '_space': '+', 'title': _("Search NPGS/GRIN"), 'tooltip': _('Search National Plant Germplasm System'), },
            {'name': 'ALAButton', '_base_uri': "http://bie.ala.org.au/search?q=%s", '_space': '+', 'title': _("Search ALA"), 'tooltip': _("Search the Atlas of Living Australia"), },
            {'name': 'IPNIButton', '_base_uri': "http://www.ipni.org/ipni/advPlantNameSearch.do?find_genus=%(genus)s&find_isAPNIRecord=on& find_isGCIRecord=on&find_isIKRecord=on&output_format=normal", '_space': ' ', 'title': _("Search IPNI"), 'tooltip': _("Search the International Plant Names Index"), },
            {'name': 'BGCIButton', '_base_uri': "http://www.bgci.org/plant_search.php?action=Find&ftrGenus=%(genus)s&ftrRedList=&ftrRedList1997=&ftrEpithet=&ftrCWR=&x=0&y=0#results", '_space': ' ', 'title': _("Search BGCI"), 'tooltip': _("Search Botanic Gardens Conservation International"), },
            {'name': 'TPLButton', '_base_uri': "http://www.theplantlist.org/tpl1.1/search?q=%(genus)s", '_space': '+', 'title': _("Search TPL"), 'tooltip': _("Search The Plant List online database"), },
            {'name': 'TropicosButton', '_base_uri': "http://tropicos.org/NameSearch.aspx?name=%(genus)s", '_space': '+', 'title': _("Search Tropicos"), 'tooltip': _("Search Tropicos (MissouriBG) online database"), },
            ]
        super().__init__()
        filename = os.path.join(paths.lib_dir(), 'plugins', 'plants',
                                'infoboxes.glade')
        self.widgets = utils.BuilderWidgets(filename)
        self.general = GeneralGenusExpander(self.widgets)
        self.add_expander(self.general)
        self.synonyms = SynonymsExpander(self.widgets)
        self.add_expander(self.synonyms)
        self.links = view.LinksExpander('notes', button_defs)
        self.add_expander(self.links)
        self.props = PropertiesExpander()
        self.add_expander(self.props)

        if 'GardenPlugin' not in pluginmgr.plugins:
            self.widgets.remove_parent('gen_nacc_label')
            self.widgets.remove_parent('gen_nacc_data')
            self.widgets.remove_parent('gen_nplants_label')
            self.widgets.remove_parent('gen_nplants_data')

    def update(self, row):
        self.general.update(row)
        self.synonyms.update(row)
        self.links.update(row)
        self.props.update(row)


db.Genus = Genus
