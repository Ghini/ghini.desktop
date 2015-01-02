class fake:
    MESSAGE_ERROR = ''
    MESSAGE_WARNING = ''
    MESSAGE_INFO = ''
    BUTTONS_OK = None
    VBox = object
    Action = Expander = ScrolledWindow = object
    EventBox = object

gtk = fake()
gobject = fake()
