#
# donor.py
#
import os
import sys

from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import SQLError

import bauble
import bauble.db as db
from bauble.editor import *
from bauble.i18n import *
import bauble.paths as paths
from bauble.types import Enum
from bauble.plugins.garden.source import Donation


def edit_callback(value):
    session = bauble.Session()
    e = DonorEditor(model=session.merge(value))
    return e.start() != None


def remove_callback(value):
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % utils.xml_safe_utf8(s)
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


donor_context_menu = [('Edit', edit_callback),
                      ('--', None),
                      ('Remove', remove_callback)]


# TODO: make sure that you can't delete the donor if donations exist, this
# should have a test

# TODO: show list of donations given by donor if searching for the donor name
# in the search view
# TODO: the donor_type could be either be character codes or possible a foreign
# key into another table
class Donor(db.Base):
    __tablename__ = 'donor'
    __mapper_args__ = {'order_by': 'name'}

    # columns
    name = Column(Unicode(72), unique=True, nullable=False)
    donor_type = Column('donor_type',
                        Enum(values=['Expedition',
                                     "Gene bank",
                                     "Botanic Garden or Arboretum",
                                     "Research/Field Station",
                                     "Staff member",
                                     "University Department",
                                     "Horticultural Association/Garden Club",
                                     "Municipal department",
                                     "Nursery/Commercial",
                                     "Individual",
                                     "Other",
                                     "Unknown",
                                     None]),
                        default=None)
    address = Column(UnicodeText)
    email = Column(Unicode(128))
    fax = Column(Unicode(64))
    tel = Column(Unicode(64))
    notes = Column(UnicodeText)

    # relations:
    donations = relation(Donation, backref=backref('donor', uselist=False))

    def __str__(self):
        return self.name



class DonorEditorView(GenericEditorView):

    # i think the field names are pretty self explanatory and tooltips
    # would be pointless
    _tooltips = {}

    def __init__(self, parent=None):
        super(DonorEditorView, self).__init__(os.path.join(paths.lib_dir(),
                                                           'plugins', 'garden',
                                                           'editors.glade'),
                                                           parent=parent)

        self.dialog = self.widgets.donor_dialog
        self.connect_dialog_close(self.dialog)
        if sys.platform == 'win32':
            import pango
            combo = self.widgets.don_type_combo
            context = combo.get_pango_context()
            font_metrics = context.get_metrics(context.get_font_description(),
                                               context.get_language())
            width = font_metrics.get_approximate_char_width()
            new_width = pango.PIXELS(width) * 20
            combo.set_size_request(new_width, -1)


    def set_accept_buttons_sensitive(self, sensitive):
        self.widgets.don_ok_button.set_sensitive(sensitive)
        self.widgets.don_next_button.set_sensitive(sensitive)


    def start(self):
        return self.dialog.run()


class DonorEditorPresenter(GenericEditorPresenter):

    widget_to_field_map = {'don_name_entry': 'name',
                           'don_type_combo': 'donor_type',
                           'don_address_textview': 'address',
                           'don_email_entry': 'email',
                           'don_tel_entry': 'tel',
                           'don_fax_entry': 'fax'
                           }

    def __init__(self, model, view):
        super(DonorEditorPresenter, self).__init__(model, view)
        model = gtk.ListStore(str)
        self.init_enum_combo('don_type_combo', 'donor_type')


        self.refresh_view()
        validator = UnicodeOrNoneValidator()
        for widget, field in self.widget_to_field_map.iteritems():
            self.assign_simple_handler(widget, field, validator)
        self.__dirty = False


    def set_model_attr(self, field, value, validator=None):
        super(DonorEditorPresenter, self).set_model_attr(field, value,
                                                         validator)
        self.__dirty = True
        self.view.set_accept_buttons_sensitive(True)


    def dirty(self):
        return self.__dirty


    def refresh_view(self):
        for widget, field in self.widget_to_field_map.iteritems():
#            debug('donor refresh(%s, %s=%s)' % (widget, field,
#                                                self.model[field]))
            self.view.set_widget_value(widget, getattr(self.model, field))


    def start(self, commit_transaction=True):
        return self.view.start()


# TODO: need to create a widget to edit the notes
class DonorEditor(GenericModelViewPresenterEditor):

    label = 'Donor'
    mnemonic_label = '_Donor'
    RESPONSE_NEXT = 11
    ok_responses = (RESPONSE_NEXT,)

    def __init__(self, model=None, parent=None):
        '''
        @param model: Donor instance or None
        @param values to enter in the model if none are give
        '''
        if model is None:
            model = Donor()
        super(DonorEditor, self).__init__(model, parent)
        self.parent = parent
        self._committed = []


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
                self.session.rollback()
                return False
            except Exception, e:
                msg = _('Unknown error when committing changes. See the '\
                       'details for more information.\n\n%s' \
                       % utils.xml_safe_utf8(e))
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

        # respond to responses
        more_committed = None
        if response == self.RESPONSE_NEXT:
            e = DonorEditor(parent=self.parent)
            more_committed = e.start()
        if more_committed is not None:
            self._committed.append(more_committed)

        return True


    def start(self):
        self.view = DonorEditorView(parent=self.parent)
        self.presenter = DonorEditorPresenter(self.model, self.view)

        # add quick response keys
        dialog = self.view.dialog
        self.attach_response(dialog, gtk.RESPONSE_OK, 'Return',
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




from bauble.view import InfoBox, InfoExpander

class GeneralDonorExpander(InfoExpander):
    '''
    displays name, number of donations, address, email, fax, tel,
    type of donor
    '''
    def __init__(self, widgets):
        super(GeneralDonorExpander, self).__init__(_('General'), widgets)
        gen_box = self.widgets.don_gen_box
        self.widgets.remove_parent(gen_box)
        self.vbox.pack_start(gen_box)


    def update(self, row):
        from textwrap import TextWrapper
        wrapper = TextWrapper(width=50, subsequent_indent='  ')
        self.set_widget_value('don_name_data', '<big>%s</big>' % \
                              utils.xml_safe(wrapper.fill(str(row.name))))
        self.set_widget_value('don_address_data', row.address)
        self.set_widget_value('don_email_data', row.email)
        self.set_widget_value('don_tel_data', row.tel)
        self.set_widget_value('don_fax_data', row.fax)
        session = bauble.Session()
        ndons = session.query(Donation).join('donor').\
                filter_by(id=row.id).count()
        self.set_widget_value('don_ndons_data', ndons)


class NotesExpander(InfoExpander):
    """
    displays notes about the donor
    """

    def __init__(self, widgets):
        super(NotesExpander, self).__init__("Notes", widgets)
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


class DonorInfoBox(InfoBox):

    def __init__(self):
        super(DonorInfoBox, self).__init__()
        glade_file = os.path.join(paths.lib_dir(), "plugins", "garden",
                            "infoboxes.glade")
        self.widgets = utils.GladeWidgets(gtk.glade.XML(glade_file))
        self.general = GeneralDonorExpander(self.widgets)
        self.add_expander(self.general)
        self.notes = NotesExpander(self.widgets)
        self.add_expander(self.notes)

    def update(self, row):
        self.general.update(row)
        self.notes.update(row)

