
import bauble
import gtk

# TODO: have two progress bars on the same dialog one for the current task
# and one for the total task

class ProgressDialog(gtk.Dialog):
    def __init__(self, parent=None, title=None):
        # TODO: if parent is None try and set it to the bauble main window
        if parent is None and bauble.app.gui is not None:
            parent = bauble.app.gui.window
        gtk.Dialog.__init__(self, parent=parent, title=title)
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
        '''returns True so the the dialog can't be closed'''
        return True
    
    
    def run(self):
        self.show_all()
        gtk.Dialog.run(self)


    def set_message(self, message):
        self.label.set_markup(message)
        
        
    def connect_cancel(self, callback):
        self.cancel_button.connect('clicked', callback)



if __name__ == '__main__':
    import gtasklet
    if __name__ == "__main__":
     win = gtk.Window()
     win.connect('delete-event', gtk.main_quit)

     button = gtk.Button('Do it.')
     def clicked(*args):
         progress_dialog = ProgressDialog()
         progress_dialog.connect('delete-event', gtk.main_quit)         
         #progress_dialog.pb.set_text('yo yo yo')
         progress_dialog.pb.set_fraction(.1)
         #progress_dialog.pb.set_pulse_step(.1)
         
         def simple_counter(numbers):
             timeout = gtasklet.WaitForTimeout(1000)
             for x in xrange(numbers):
                 print x
                 #progress_dialog.pb.pulse()
                 progress_dialog.pb.set_fraction((x+.1)*.1)
                 yield timeout
                 gtasklet.get_event()
         gtasklet.run(simple_counter(10))
         progress_dialog.run()
     button.connect('clicked', clicked)
     win.add(button)     
     win.show_all()
     gtk.main()