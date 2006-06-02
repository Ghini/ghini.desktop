#
# utils module
#

import imp, os, sys, re
import bauble
import gtk
from bauble.utils.log import debug

def search_tree_model(model, data, func=lambda row, data: row[0] == data):
    '''
    model: the tree model the search
    data: what we are searching for
    func: the function to use to compare each row in the model, the default
    signatude is lambda row, data: row[0] == data
    '''
    if not model:
        return None
    for row in model:
        if func(row, data):
            return row
        result = search_tree_model(row.iterchildren(), data, func)
	if result:
	    return result
    return None


def set_combo_from_value(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    find value in combo model and set it as active, else raise ValueError
    cmp(row, value) is the a function to use for comparison
    NOTE: 
    '''
    model = combo.get_model()    
    match = search_tree_model(model, value, cmp)
    if match is None:
        raise ValueError('set_combo_from_value() - could not find value in '\
                         'combo: %s' % value)
    combo.set_active_iter(match.iter)

    
def combo_get_value_iter(combo, value, cmp=lambda row, value: row[0] == value):
    model = combo.get_model()
    match = search_tree_model(model, value, cmp)
    if match is not None:
        return match.iter
    return None


def set_widget_value(glade_xml, widget_name, value, markup=True, default=None):
    '''
    glade_xml: the glade_file to get the widget from
    widget_name: the name of the widget
    value: the value to put in the widget
    markup: whether or not
    default: the default value to put in the widget if the value is None
    
    NOTE: any values passed in for widgets that expect a string will call
    the values __str__ method    
    '''

    w = glade_xml.get_widget(widget_name)
    if value is None:  # set the value from the default
        if isinstance(w,(gtk.Label, gtk.TextView, gtk.Entry)) and default is None:
            value = ''
        else:
            value = default
        
    if isinstance(w, gtk.Label):
        #w.set_text(str(value))
        # FIXME: some of the enum values that have <not set> as a values
        # will give errors here, but we can't escape the string because
        # if someone does pass something that needs to be marked up
        # then it won't display as intended, maybe BaubleTable.markup()
        # should be responsible for returning a properly escaped values
        # or we should just catch the error(is there an error) and call
        # set_text if set_markup fails
        if markup: 
            w.set_markup(str(value))
        else:
            w.set_text(str(value))
    elif isinstance(w, gtk.TextView):
        w.get_buffer().set_text(str(value))
    elif isinstance(w, gtk.Entry):
        w.set_text(str(value))
    elif isinstance(w, gtk.ComboBox): # TODO: what about comboentry
        # TODO: what if None is in the model
        i = combo_get_value_iter(w, value)
        if i is not None:
            w.set_active_iter(i)
        elif w.get_model() is not None:
            w.set_active(-1)
#        if value is None:
#            if w.get_model() is not None:
#                w.set_active(-1)
#        else:
#            set_combo_from_value(w, value)	
    elif isinstance(w, (gtk.ToggleButton, gtk.CheckButton, gtk.RadioButton)): 
        if value is True:     
            w.set_active(True)
        elif value is False: # how come i have to unset inconsistent for False?
            w.set_inconsistent(False)
            w.set_active(False)
        else:
            w.set_inconsistent(True)            
    else:
        raise TypeError('don\'t know how to handle the widget type %s with '\
		                'name %s' % (type(w), widget_name))

# TODO: if i escape the messages that come in then my own markup doesn't 
# work, what really needs to be done is make sure that any exception that
# are going to be passed to one of these dialogs should be escaped before 
# coming through

def message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK):
    try: # this might get called before bauble has started
        parent = bauble.app.gui.window
    except:
	parent = None	
    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
			 parent=parent,
			 type=type, buttons=buttons)
    d.set_markup(msg)
    r = d.run()
    d.destroy()
    return r
    

# TODO: it would be nice to implement a yes_or_no method that asks from the 
# console if there is no gui. is it possible to know if we have a terminal
# to write to
def yes_no_dialog(msg, parent=None):
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.app.gui.window
        except:
            parent = None

    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         parent=parent,
                         type=gtk.MESSAGE_QUESTION,
                         buttons = gtk.BUTTONS_YES_NO)            
    d.set_markup(msg)    
    r = d.run()
    d.destroy()
    return r == gtk.RESPONSE_YES


#
# TODO: give the button the default focus instead of the expander
#
def message_details_dialog(msg, details, type=gtk.MESSAGE_INFO, 
                           buttons=gtk.BUTTONS_OK):    
    try: # this might get called before bauble has started
        parent = bauble.app.gui.window	
    except:	
        parent = None
    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         parent=parent,type=type, buttons=buttons)        
    d.set_markup(msg)    
    expand = gtk.Expander("Details")    
    text_view = gtk.TextView()
    text_view.set_editable(False)
    text_view.set_wrap_mode(gtk.WRAP_WORD)
    tb = gtk.TextBuffer()
    tb.set_text(details)
    text_view.set_buffer(tb)
    sw = gtk.ScrolledWindow()
    sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
    sw.add(text_view)    
    expand.add(sw)
    d.vbox.pack_start(expand)
    ok_button = d.action_area.get_children()[0]
    d.set_focus(ok_button)
    d.show_all()
    r = d.run()
    d.destroy()
    return r


def startfile(filename):
    if sys.platform == 'win32':
        try:
            os.startfile(filename)
        except WindowsError, e: # probably no file association
            msg = "Could not open pdf file.\n\n%s" % str(e)
            message_dialog(msg)        
    elif sys.platform == 'linux2':
        # FIXME: need to determine if gnome or kde
        os.system("gnome-open " + filename)
    else:
        raise Exception("bauble.utils.startfile(): can't open file:" + filename)
   
   
