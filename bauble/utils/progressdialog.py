
import bauble
import gtk

# TODO: have two progress bars on the same dialog one for the current task
# and one for the total task

class ProgressDialog(gtk.Dialog):

    def __init__(self, parent=None, title=None):
        # TODO: if parent is None try and set it to the bauble main window
        if parent is None and bauble.gui is not None:
            parent = bauble.gui.window
        gtk.Dialog.__init__(self, parent=parent, title=title,
                            flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT)
        self.set_resizable(False)
        self.cancel_button = self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.box = gtk.VBox()
        self.label = gtk.Label()
        self.label.set_alignment(0.0, 0.5)
        self.box.pack_start(self.label, padding=10)
        self.pb = gtk.ProgressBar()
        self.box.pack_start(self.pb, padding=10)
        self.vbox.add(self.box)
        self.connect('delete-event', self.on_delete)


    def on_delete(self, *args):
        """returns True so the the dialog can't be closed"""
        return True


    def run(self):
        self.show_all()
        gtk.Dialog.run(self)


    def set_message(self, message):
        self.label.set_markup(message)


    def connect_cancel(self, callback):
        self.cancel_button.connect('clicked', callback)
