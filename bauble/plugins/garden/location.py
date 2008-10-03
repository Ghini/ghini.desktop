#
# location.py
#
import os, traceback
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.session import object_session
from sqlalchemy.exceptions import SQLError
import bauble
from bauble.i18n import _
from bauble.editor import *
import bauble.utils as utils
import bauble.paths as paths


def edit_callback(value):
    session = bauble.Session()
    e = LocationEditor(model=session.merge(value))
    return e.start() != None


def add_plant_callback(value):
    session = bauble.Session()
    from bauble.plugins.garden.plant import PlantEditor
    e = PlantEditor(model=Plant(location=session.merge(value)))
    return e.start() != None


def remove_callback(value):
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % \
          utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = bauble.Session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    return True


loc_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Add plant', add_plant_callback),
                    ('--', None),
                    ('Remove', remove_callback)]


def loc_markup_func(location):
    if location.description is not None:
        return str(location), str(location.description)
    else:
        return str(location)


class Location(bauble.Base):
    __tablename__ = 'location'
    __mapper_args__ = {'order_by': 'site'}

    # columns
    site = Column(Unicode(64), unique=True, nullable=False)
    description = Column(UnicodeText)

    # relations
    plants = relation('Plant', backref=backref('location', uselist=False))

    def __str__(self):
        return str(self.site)

# location_table = bauble.Table('location', bauble.metadata,
#                        Column('id', Integer, primary_key=True),
#                        Column('site', Unicode(64), unique=True,nullable=False),
#                        Column('description', UnicodeText))


# class Location(bauble.BaubleMapper):
#     def __str__(self):
#         return self.site


# from bauble.plugins.garden.plant import Plant

# mapper(Location, location_table, order_by='site',
#        properties={'plants': relation(Plant, backref=backref('location',
#                                                              uselist=False))})


class LocationEditorView(GenericEditorView):

    #source_expanded_pref = 'editor.accesssion.source.expanded'
    _tooltips = {
        'loc_location_entry': _('The site is the name that you will use '\
                                'later to refer to this location.'),
        'loc_desc_textview': _('Any information that might be relevant to '\
                               'the location such as where it is or what\'s '\
                               'it\'s purpose')
        }

    def __init__(self, parent=None):
        GenericEditorView.__init__(self, os.path.join(paths.lib_dir(),
                                                      'plugins', 'garden',
                                                      'editors.glade'),
                                   parent=parent)
        self.dialog = self.widgets.location_dialog
        self.dialog.set_transient_for(parent)
        self.connect_dialog_close(self.widgets.location_dialog)

        self.use_ok_and_add = True
        if parent != bauble.gui.window:
            self.use_ok_and_add = False


    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.loc_ok_button.set_sensitive(sensitive)
        self.widgets.loc_ok_and_add_button.set_sensitive(self.use_ok_and_add \
                                                         and sensitive)
        self.widgets.loc_next_button.set_sensitive(sensitive)


    def start(self):
        return self.dialog.run()


class LocationEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'loc_location_entry': 'site',
                           'loc_desc_textview': 'description'}

    def __init__(self, model, view):
        '''
        model: should be an instance of class Accession
        view: should be an instance of AccessionEditorView
        '''
        GenericEditorPresenter.__init__(self, model, view)
        self.session = object_session(model)

        # initialize widgets
        self.refresh_view() # put model values in view

        # connect signals
        self.assign_simple_handler('loc_location_entry', 'site',
                                   UnicodeOrNoneValidator())
        self.assign_simple_handler('loc_desc_textview', 'description',
                                   UnicodeOrNoneValidator())
        self.__dirty = False


    def set_model_attr(self, model, field, validator=None):
        super(LocationEditorPresenter, self).set_model_attr(model, field,
                                                            validator)
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(model.site != None)


    def dirty(self):
        return self.__dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
            value = self.model[field]
            self.view.set_widget_value(widget, value)


    def start(self):
        return self.view.start()


class LocationEditor(GenericModelViewPresenterEditor):

    label = 'Location'
    mnemonic_label = '_Location'

    # these have to correspond to the response values in the view
    RESPONSE_OK_AND_ADD = 11
    RESPONSE_NEXT = 22
    ok_responses = (RESPONSE_OK_AND_ADD, RESPONSE_NEXT)


    def __init__(self, model=None, parent=None):
        '''
        @param model: Location instance or None
        @param parent: the parent widget or None
        '''
        # view and presenter are created in self.start()
        self.view = None
        self.presenter = None
        if model is None:
            model = Location()
        super(LocationEditor, self).__init__(self, model, parent)
        if parent is None:
            parent = bauble.gui.window
        self.parent = parent
        self._committed = []


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = 'Are you sure you want to lose your changes?'
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s') % \
                      utils.xml_safe_utf8(e.orig)
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                        'details for more information.\n\n%s') % \
                        utils.xml_safe_utf8(e)
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                self.session.rollback()
                return False
        elif self.presenter.dirty() \
                 and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = LocationEditor(parent=self.parent)
            more_committed = e.start()
        elif response == self.RESPONSE_OK_AND_ADD:
            from bauble.plugins.garden.plant import PlantEditor
            e = PlantEditor(Plant(location=self.model), self.parent)
            more_committed = e.start()

        if more_committed is not None:
            if isinstance(more_committed, list):
                self._committed.extend(more_committed)
            else:
                self._committed.append(more_committed)

        return True


    def start(self):
        self.view = LocationEditorView(parent=self.parent)
        self.presenter = LocationEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_OK_AND_ADD, 'k',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(dialog, self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)

        while True:
            response = self.presenter.start()
            self.view.save_state() # should view or presenter save state
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        return self._committed


from bauble.view import InfoBox, InfoExpander, PropertiesExpander


class GeneralLocationExpander(InfoExpander):
    """
    general expander for the PlantInfoBox
    """

    def __init__(self, widgets):
        '''
        '''
        InfoExpander.__init__(self, "General", widgets)
        general_box = self.widgets.loc_gen_box
        self.widgets.remove_parent(general_box)
        self.vbox.pack_start(general_box)


    def update(self, row):
        '''
        '''
        self.set_widget_value('loc_site_data',
                              '<big>%s</big>' % utils.xml_safe(str(row.site)))
        session = object_session(row)
        nplants = session.query(Plant).filter_by(location_id=row.id).count()
        self.set_widget_value('loc_nplants_data', nplants)


class DescriptionExpander(InfoExpander):
    """
    the location description
    """

    def __init__(self, widgets):
        InfoExpander.__init__(self, "Descripion", widgets)
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
            self.set_widget_value('loc_descr_data', str(row.description))


class LocationInfoBox(InfoBox):
    """
    an InfoBox for a Location table row
    """

    def __init__(self):
        '''
        '''
        InfoBox.__init__(self)
        glade_file = os.path.join(paths.lib_dir(), "plugins", "garden",
                                  "infoboxes.glade")
        self.widgets = utils.GladeWidgets(glade_file)
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
#
# import here to avoid circular dependencies
#
#from bauble.plugins.garden.plant import PlantEditor
