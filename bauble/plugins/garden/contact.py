#
# contact.py
#
import os
import sys

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import SQLError

import bauble
import bauble.db as db
from bauble.editor import *
import bauble.paths as paths
from bauble.types import Enum
from bauble.view import Action


def edit_callback(contacts):
    contact = contacts[0]
    e = ContactEditor(model=contact)
    return e.start() != None


def remove_callback(contacts):
    contact = contacts[0]
    s = '%s: %s' % (contact.__class__.__name__, str(contact))
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe_utf8(s)
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = db.Session()
        obj = session.query(Contact).get(contact.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)
    finally:
        session.close()
    return True


edit_action = Action('contact_edit', ('_Edit'), callback=edit_callback,
                     accelerator='<ctrl>e')
remove_action = Action('contact_remove', ('_Remove'), callback=remove_callback,
                       accelerator='<delete>', multiselect=True)

contact_context_menu = [edit_action, remove_action]


# TODO: **important** the contact_type could be either be character
# codes or something so that they can be translated

contact_type_values = {u'Expedition': _('Expedition'),
                     u'GeneBank': _('Gene Bank'),
                     u'BG/Arboretum': _('Botanic Garden or Arboretum'),
                     u'Research/FieldStation': _('Research/Field Station'),
                     u'Staff': _('Staff member'),
                     u'UniversityDepartment': _('University Department'),
                     u'Hort/GardenClub': \
                         _('Horticultural Association/Garden Club'),
                     u'MunicipalDepartment': _('Municipal department'),
                     u'Nursery/Commercial': _('Nursery/Commercial'),
                     u'Individual': _('Individual'),
                     u'Other': _('Other'),
                     u'Unknown': _('Unknown'),
                     None: _('')}

class Contact(db.Base):
    __tablename__ = 'contact'
    __mapper_args__ = {'order_by': 'name'}

    # columns
    name = Column(Unicode(72), unique=True, nullable=False)
    contact_type = Column('contact_type',
                          Enum(values=contact_type_values.keys()), default=None)
    address = Column(UnicodeText)
    email = Column(Unicode(128))
    fax = Column(Unicode(64))
    tel = Column(Unicode(64))
    notes = Column(UnicodeText)

    # relations:

    # TODO: make a list relation to all the accession from this
    # contact via the accession_source table
    #accessions = relation('Accession')
    #donations = relation(Donation, backref=backref('donor', uselist=False))

    def __str__(self):
        return self.name



class ContactEditorView(GenericEditorView):

    # i think the field names are pretty self explanatory and tooltips
    # would be pointless
    _tooltips = {}

    def __init__(self, parent=None):
        filename = os.path.join(paths.lib_dir(), 'plugins', 'garden',
                                'contact_editor.glade')
        super(ContactEditorView, self).__init__(filename, parent=parent)
        self.set_accept_buttons_sensitive(False)
        self.init_translatable_combo('don_type_combo', contact_type_values)
        if sys.platform == 'win32':
            # TODO: is this character width fix still necessary
            import pango
            combo = self.widgets.don_type_combo
            context = combo.get_pango_context()
            font_metrics = context.get_metrics(context.get_font_description(),
                                               context.get_language())
            width = font_metrics.get_approximate_char_width()
            new_width = pango.PIXELS(width) * 20
            combo.set_size_request(new_width, -1)


    def get_window(self):
        return self.widgets.contact_dialog


    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.don_ok_button.set_sensitive(sensitive)
        self.widgets.don_next_button.set_sensitive(sensitive)


    def start(self):
        return self.get_window().run()


class ContactEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'don_name_entry': 'name',
                           'don_type_combo': 'contact_type',
                           'don_address_textview': 'address',
                           'don_email_entry': 'email',
                           'don_tel_entry': 'tel',
                           'don_fax_entry': 'fax'
                           }

    def __init__(self, model, view):
        super(ContactEditorPresenter, self).__init__(model, view)
        self.refresh_view()
        validator = UnicodeOrNoneValidator()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field, validator)
        self.__dirty = False


    def set_model_attr(self, field, value, validator=None):
        super(ContactEditorPresenter, self).set_model_attr(field, value,
                                                         validator)
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(True)


    def dirty(self):
        return self.__dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
#            debug('contact refresh(%s, %s=%s)' % (widget, field,
#                                                self.model[field]))
            self.view.set_widget_value(widget, getattr(self.model, field))

        self.view.set_widget_value('don_type_combo',
                                   contact_type_values[self.model.contact_type],
                                   index=1)


    def start(self):
        r = self.view.start()
        return r


# TODO: need to create a widget to edit the notes column

class ContactEditor(GenericModelViewPresenterEditor):

    RESPONSE_NEXT = 11
    ok_responses = (RESPONSE_NEXT,)

    def __init__(self, model=None, parent=None):
        '''
        @param model: Contact instance or None
        @param values to enter in the model if none are give
        '''
        if not model:
            model = Contact()
        super(ContactEditor, self).__init__(model, parent)
        self.parent = parent
        self._committed = []

        view = ContactEditorView(parent=self.parent)
        self.presenter = ContactEditorPresenter(self.model, view)

        # add quick response keys
        self.attach_response(view.get_window(), gtk.RESPONSE_OK, 'Return',
                             gtk.gdk.CONTROL_MASK)
        self.attach_response(view.get_window(), self.RESPONSE_NEXT, 'n',
                             gtk.gdk.CONTROL_MASK)


    def handle_response(self, response):
        '''
        handle the response from self.presenter.start() in self.start()
        '''
        not_ok_msg = _('Are you sure you want to lose your changes?')
        if response == gtk.RESPONSE_OK or response in self.ok_responses:
            try:
                if self.presenter.dirty():
                    self.commit_changes()
                    self._committed.append(self.model)
            except SQLError, e:
                msg = _('Error committing changes.\n\n%s' \
                        % utils.xml_safe_utf8(e.orig))
                utils.message_details_dialog(msg, str(e), gtk.MESSAGE_ERROR)
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                       'details for more information.\n\n%s' \
                       % utils.xml_safe_utf8(e))
                utils.message_details_dialog(msg, traceback.format_exc(),
                                             gtk.MESSAGE_ERROR)
                return False
        elif self.presenter.dirty() and utils.yes_no_dialog(not_ok_msg) \
                 or not self.presenter.dirty():
            self.session.rollback()
            return True
        else:
            return False

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            self.presenter.cleanup()
            e = ContactEditor(parent=self.parent)
            more_committed = e.start()
        if more_committed is not None:
            self._committed.append(more_committed)

        return True


    def start(self):
        while True:
            response = self.presenter.start()
            self.presenter.view.save_state()
            if self.handle_response(response):
                break

        self.session.close() # cleanup session
        self.presenter.cleanup()
        return self._committed



from bauble.view import InfoBox, InfoExpander

class GeneralContactExpander(InfoExpander):
    '''
    displays name, number of donations, address, email, fax, tel,
    type of contact
    '''
    def __init__(self, widgets):
        super(GeneralContactExpander, self).__init__(_('General'), widgets)
        gen_box = self.widgets.don_gen_box
        self.widgets.remove_parent(gen_box)
        self.vbox.pack_start(gen_box)


    def update(self, row):
        from textwrap import TextWrapper
        wrapper = TextWrapper(width=50, subsequent_indent='  ')
        self.set_widget_value('don_name_data', '<big>%s</big>' %
                              utils.xml_safe_utf8(row.name))
        self.set_widget_value('don_address_data',
                              utils.xml_safe_utf8(row.address))
        self.set_widget_value('don_email_data', utils.xml_safe_utf8(row.email))
        self.set_widget_value('don_tel_data', utils.xml_safe_utf8(row.tel))
        self.set_widget_value('don_fax_data', utils.xml_safe_utf8(row.tel))
        from bauble.plugins.garden.source import SourceContact
        source_contact = SourceContact.__table__
        nacc = select([source_contact.c.id],
                      source_contact.c.contact_id==row.id).\
                      count().execute().fetchone()[0]
        self.set_widget_value('don_nacc_data', nacc)



class NotesExpander(InfoExpander):
    """
    displays notes about the contact
    """

    def __init__(self, widgets):
        super(NotesExpander, self).__init__(_("Notes"), widgets)
        notes_box = self.widgets.don_notes_box
        self.widgets.remove_parent(notes_box)
        self.vbox.pack_start(notes_box)


    def update(self, row):
        if row.notes is None:
            self.set_sensitive(False)
            self.set_expanded(False)
        else:
            # TODO: get expanded state from prefs
            self.set_sensitive(True)
            self.set_widget_value('don_notes_data', row.notes)


class ContactInfoBox(InfoBox):

    def __init__(self):
        super(ContactInfoBox, self).__init__()
        filename = os.path.join(paths.lib_dir(), "plugins", "garden",
                                "contact_infobox.glade")
        self.widgets = utils.load_widgets(filename)
        self.general = GeneralContactExpander(self.widgets)
        self.add_expander(self.general)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)

    def update(self, row):
        self.general.update(row)
        self.notes.update(row)

