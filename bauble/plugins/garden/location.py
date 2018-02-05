# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2015 Mario Frasca <mario@anche.no>.
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
# location.py
#
import os
import traceback
import gtk

import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

from sqlalchemy import Column, Unicode, UnicodeText
from sqlalchemy.orm import relation, backref, validates
from sqlalchemy.orm.session import object_session
from sqlalchemy.exc import DBAPIError


import bauble
import bauble.db as db
from bauble.editor import GenericModelViewPresenterEditor, GenericEditorView, \
    GenericEditorPresenter, UnicodeOrNoneValidator
import bauble.utils as utils
import bauble.paths as paths
from bauble.view import Action


def edit_callback(locations):
    e = LocationEditor(model=locations[0])
    return e.start() is not None


def add_plants_callback(locations):
    # create a temporary session so that the temporary plant doesn't
    # get added to the accession
    session = db.Session()
    loc = session.merge(locations[0])
    from bauble.plugins.garden.plant import Plant, PlantEditor
    e = PlantEditor(model=Plant(location=loc))
    session.close()
    return e.start() is not None


def remove_callback(locations):
    loc = locations[0]
    s = '%s: %s' % (loc.__class__.__name__, str(loc))
    if len(loc.plants) > 0:
        msg = _('Please remove the plants from <b>%(location)s</b> '
                'before deleting it.') % {'location': loc}
        utils.message_dialog(msg, gtk.MESSAGE_WARNING)
        return
    msg = _("Are you sure you want to remove %s?") % \
        utils.xml_safe(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = db.Session()
        obj = session.query(Location).get(loc.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True

edit_action = Action('loc_edit', _('_Edit'),
                     callback=edit_callback,
                     accelerator='<ctrl>e')
add_plant_action = Action('loc_add_plant', _('_Add plants'),
                          callback=add_plants_callback,
                          accelerator='<ctrl>k')
remove_action = Action('loc_remove', _('_Delete'),
                       callback=remove_callback,
                       accelerator='<ctrl>Delete', multiselect=True)

loc_context_menu = [edit_action, add_plant_action, remove_action]


class Location(db.Base, db.Serializable):
    """
    :Table name: location

    :Columns:
        *name*:

        *description*:

    :Relation:
        *plants*:

    """
    __tablename__ = 'location'
    __mapper_args__ = {'order_by': 'name'}

    # columns
    # refers to beds by unique codes
    code = Column(Unicode(12), unique=True, nullable=False)
    name = Column(Unicode(64))
    description = Column(UnicodeText)

    # relations
    plants = relation('Plant', backref=backref('location', uselist=False))

    def search_view_markup_pair(self):
        '''provide the two lines describing object for SearchView row.
        '''
        if self.description is not None:
            return (utils.xml_safe(str(self)),
                    utils.xml_safe(str(self.description)))
        else:
            return utils.xml_safe(str(self))

    @validates('code', 'name')
    def validate_stripping(self, key, value):
        if value is None:
            return None
        return value.strip()

    def __str__(self):
        if self.name:
            return '(%s) %s' % (self.code, self.name)
        else:
            return str(self.code)

    def has_accessions(self):
        '''true if location is linked to at least one accession
        '''

        return False

    @classmethod
    def retrieve(cls, session, keys):
        try:
            return session.query(cls).filter(
                cls.code == keys['code']).one()
        except:
            return None

    def top_level_count(self):
        accessions = set(p.accession for p in self.plants)
        species = set(a.species for a in accessions)
        genera = set(s.genus for s in species)
        return {(1, 'Locations'): 1,
                (2, 'Plantings'): len(self.plants),
                (3, 'Living plants'): sum(p.quantity for p in self.plants),
                (4, 'Accessions'): set(a.id for a in accessions),
                (5, 'Species'): set(s.id for s in species),
                (6, 'Genera'): set(g.id for g in genera),
                (7, 'Families'): set(g.family.id for g in genera),
                (8, 'Sources'): set([a.source.source_detail.id
                                     for a in accessions
                                     if a.source and a.source.source_detail])}


def mergevalues(value1, value2, formatter):
    """return the common value
    """

    if value1 == value2:
        value = value1 or ''
    elif value1 and value2:
        value = formatter % (value1, value2)
    else:
        value = value1 or value2 or ''
    return value


class LocationEditorView(GenericEditorView):

    #source_expanded_pref = 'editor.accesssion.source.expanded'
    _tooltips = {
        'loc_name_entry': _('The name that you will use '
                            'later to refer to this location.'),
        'loc_desc_textview': _('Any information that might be relevant to '
                               'the location such as where it is or what\'s '
                               'its purpose')
        }

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(),
                                                      'plugins', 'garden',
                                                      'loc_editor.glade'),
                                   parent=parent)
        self.use_ok_and_add = True
        self.set_accept_buttons_sensitive(False)
        # if the parent isn't the main bauble window then we assume
        # that the LocationEditor was opened from the PlantEditor and
        # so we shouldn't enable adding more plants...this is a bit of
        # a hack but it serves our purposes
        if bauble.gui and parent != bauble.gui.window:
            self.use_ok_and_add = False

    def get_window(self):
        return self.widgets.location_dialog

    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.loc_ok_button.set_sensitive(sensitive)
        self.widgets.loc_ok_and_add_button.set_sensitive(self.use_ok_and_add
                                                         and sensitive)
        self.widgets.loc_next_button.set_sensitive(sensitive)

    def start(self):
        return self.get_window().run()


class LocationEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'loc_name_entry': 'name',
                           'loc_code_entry': 'code',
                           'loc_desc_textview': 'description'}

    def __init__(self, model, view):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.create_toolbar()
        self.session = object_session(model)
        self._dirty = False

        # initialize widgets
        self.refresh_view()  # put model values in view

        # connect signals
        self.assign_simple_handler('loc_name_entry', 'name',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('loc_code_entry', 'code',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('loc_desc_textview', 'description',
                                   UnicodeOrNoneValidator())
        self.refresh_sensitivity()
        if self.model not in self.session.new:
            self.view.widgets.loc_ok_and_add_button.set_sensitive(True)

        # the merger danger zone
        self.merger_candidate = None

        def on_location_select(location):
            logger.debug('merger candidate: %s' % location)
            self.merger_candidate = location

        from bauble.plugins.garden import init_location_comboentry
        init_location_comboentry(self, self.view.widgets.loc_merge_comboentry,
                                 on_location_select)
        self.view.connect('loc_merge_button', 'clicked',
                          self.on_loc_merge_button_clicked)

    def on_loc_merge_button_clicked(self, entry, *args):
        entry_widget = self.view.widgets.loc_merge_entry
        if self.has_problems(entry_widget):
            logger.warning("'%s' does not identify a valid location" %
                           entry_widget.get_text())
            return
        logger.debug('request to merge %s into %s' %
                     (self.model, self.merger_candidate, ))

        md = gtk.MessageDialog(
            self.view.get_window(), gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO,
            (_('please confirm merging %(1)s into %(2)s') %
             {'1': self.model, '2': self.merger_candidate, }))
        confirm = md.run()
        md.destroy()

        if not confirm:
            return

        # step 0: swap `model` and `merger_candidate` objects: we are going
        # to keep model and delete merger_candidate.
        self.model, self.merger_candidate = self.merger_candidate, self.model

        # step 1: update tables plant and plant_changes, by altering all
        # references to self.merger_candidate into references to self.model.
        from bauble.plugins.garden.plant import Plant, PlantChange
        for p in self.session.query(Plant).filter(
                Plant.location == self.merger_candidate).all():
            p.location = self.model
        for p in self.session.query(PlantChange).filter(
                PlantChange.from_location == self.merger_candidate).all():
            p.from_location = self.model
        for p in self.session.query(PlantChange).filter(
                PlantChange.to_location == self.merger_candidate).all():
            p.to_location = self.model

        # step 2: merge model and merger_candidate  `description` and `name`
        # fields, mark there's a problem to solve there.
        self.view.widget_set_value('loc_code_entry',
                                   getattr(self.model, 'code'))

        buf = self.view.widgets.loc_desc_textview.get_buffer()
        self.view.widget_set_value(
            'loc_desc_textview', mergevalues(
                buf.get_text(*buf.get_bounds()),
                getattr(self.merger_candidate, 'description'),
                "%s\n---------\n%s"))
        self.view.widget_set_value(
            'loc_name_entry', mergevalues(
                self.view.widgets.loc_name_entry.get_text(),
                getattr(self.merger_candidate, 'name'),
                "%s\n---------\n%s"))
        #self.add_problem('MERGED', self.view.widgets.loc_desc_textview)

        # step 3: delete self.merger_candidate and clean the entry
        self.session.delete(self.merger_candidate)
        self.view.widget_set_value('loc_merge_comboentry', '')

        # step 4: collapse the expander
        self.view.widgets.danger_zone.set_expanded(False)

    def refresh_sensitivity(self):
        sensitive = False
        ignore = ('id')
        if self.is_dirty() and not \
                utils.get_invalid_columns(self.model, ignore_columns=ignore):
            sensitive = True
        self.view.set_accept_buttons_sensitive(sensitive)

    def set_model_attr(self, attr, value, validator=None):
        super(LocationEditorPresenter, self).\
            set_model_attr(attr, value, validator)
        self._dirty = True
        self.refresh_sensitivity()

    def is_dirty(self):
        return self._dirty

    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = getattr(self.model, field)
            self.view.widget_set_value(widget, value)

    def start(self):
        r = self.view.start()
        return r


class LocationEditor(GenericModelViewPresenterEditor):

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)

    def __init__(self, model=None, parent=None):
        '''
        :param model: Location instance or None
        :param parent: the parent widget or None
        '''
        # view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Location()
        super(LocationEditor, self).__init__(model, parent)
        if not parent and bauble.gui:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []

        view = LocationEditorView(parent=self.parent)
        self.presenter = LocationEditorPresenter(self.model, view)

    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.is_dirty():
                    self.commit_changes()
                self._committed.append(self.model)
            except DBAPIError, e:
                msg = _('Error committing changes.\n\n%s') % \
                    utils.xml_safe(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '
                        'details for more information.\n\n%s') % \
                    utils.xml_safe(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.is_dirty() \
                and utils.yes_no_dialog(not_ok_msg) \
                or not self.presenter.is_dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = LocationEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            from bauble.plugins.garden.plant import PlantEditor, Plant
            e = PlantEditor(Plant(location=self.model), self.parent)
            more_committed = e.start()
        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True

    def start(self):
        """
        Started the LocationEditor and return the committed Location objects.
        """
        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break
        self.session.close()
        self.presenter.cleanup()
        return self._committed


from bauble.view import InfoBox, InfoExpander, PropertiesExpander


class GeneralLocationExpander(InfoExpander):
    """
    general expander for the PlantInfoBox
    """

    def __init__(self, widgets):
        '''
        '''
        InfoExpander.__init__(self, _("General"), widgets)
        general_box = self.widgets.loc_gen_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)
        self.current_obj = None

        def on_nplants_clicked(*args):
            cmd = 'plant where location.code="%s"' % self.current_obj.code
            bauble.gui.send_command(cmd)
        utils.make_label_clickable(self.widgets.loc_nplants_data,
                                   on_nplants_clicked)

    def update(self, row):
        '''
        '''
        self.current_obj = row
        from bauble.plugins.garden.plant import Plant
        self.widget_set_value('loc_name_data',
                              '<big>%s</big>' % utils.xml_safe(str(row)),
                              markup=True)
        session = object_session(row)
        nplants = session.query(Plant).filter_by(location_id=row.id).count()
        self.widget_set_value('loc_nplants_data', nplants)


class DescriptionExpander(InfoExpander):
    """
    The location description
    """

    def __init__(self, widgets):
        InfoExpander.__init__(self, _("Description"), widgets)
        descr_box = self.widgets.loc_descr_box
        self.widgets.remove_parent(descr_box)
        self.vbox.pack_start(descr_box)

    def update(self, row):
        '''
        '''
        if row.description is None:
            self.set_expanded(False)
            self.set_sensitive(False)
        else:
            self.set_expanded(True)
            self.set_sensitive(True)
            self.widget_set_value('loc_descr_data', str(row.description))


class LocationInfoBox(InfoBox):
    """
    an InfoBox for a Location table row
    """

    def __init__(self):
        '''
        '''
        InfoBox.__init__(self)
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "loc_infobox.glade")
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralLocationExpander(self.widgets)
        self.add_expander(self.general)
        self.description = DescriptionExpander(self.widgets)
        self.add_expander(self.description)
        self.props = PropertiesExpander()
        self.add_expander(self.props)

    def update(self, row):
        '''
        '''
        self.general.update(row)
        self.description.update(row)
        self.props.update(row)
