class fake:
    MESSAGE_ERROR = ''
    MESSAGE_WARNING = ''
    MESSAGE_INFO = ''
    DIALOG_MODAL = DIALOG_DESTROY_WITH_PARENT = BUTTONS_OK = None
    VBox = object
    Menu = Action = Expander = ScrolledWindow = object
    EventBox = object

    def MessageDialog(*args):
        pass

gtk = fake()
gobject = fake()
