#
# utils module
#

import imp, os, sys, re
import bauble
import bauble.paths as paths
from bauble.i18n import *
import gtk, gtk.glade
from bauble.utils.log import debug, warning
import xml.sax.saxutils as saxutils

default_icon = os.path.join(paths.lib_dir(), "images", "icon.svg")

# TODO: this util module might need to be split up if it gets much larger
# we could have a utils.gtk and utils.sql
#

#def search_tree_model(model, data, func=lambda row, data: row[0] == data):
#    '''
#    return the first occurence of data found in model
#
#    @param model: the tree model to search
#    @param data: what we are searching for
#    @param func: the function to use to compare each row in the model, the
#        default is C{lambda row, data: row[0] == data}
#    '''
#    result = None
#    for row in model:
#        if func(row, data):
#            return row
#        result = search_tree_model(row.iterchildren(), data, func)
#    return result


def find_dependent_tables(table, metadata=None):
    '''
    return an iterator with all tables the depend on table
    '''
    if metadata is None:
        metadata = bauble.metadata
    result = []
    def _impl(t2):
        for tbl in metadata.table_iterator():
            for col in tbl.c:
                for fk in col.foreign_keys:
                    if fk.column.table == t2:
                        if tbl not in result and tbl is not table:
#                            debug('append: %s' % tbl.name)
                            result.append(tbl)
                            _impl(tbl)
    _impl(table)
#    debug([r.name for r in result])
    return metadata.table_iterator(tables=result)


class GladeWidgets(dict):
    '''
    dictionary and attribute access for widgets
    '''

    def __init__(self, glade_xml):
        '''
        @params glade_xml: a gtk.glade.XML object
        '''
        if isinstance(glade_xml, str):
            self.glade_xml = gtk.glade.XML(glade_xml)
        else:
            self.glade_xml = glade_xml


    def __getitem__(self, name):
        '''
        @param name:
        '''
        # TODO: raise a key error if there is no widget
        return self.glade_xml.get_widget(name)


    def __getattr__(self, name):
        '''
        @param name:
        '''
        return self.glade_xml.get_widget(name)


    def remove_parent(self, widget):
        # if parent is the last reference to widget then widget may be
        # automatically destroyed
        if isinstance(widget, str):
            w = self[widget]
        else:
            w = widget
        parent = w.get_parent()
        if parent is not None:
            parent.remove(w)


    def signal_autoconnect(self, handlers):
        self.glade_xml.signal_autoconnect(handlers)


def tree_model_has(tree, value):
    return len(search_tree_model(tree, value)) > 0


def search_tree_model(parent, data, func=lambda row, data: row[0] == data):
    '''
    return a list of tree iters to all occurences of data in model
    '''
    results = []
    for row in parent:
        search_tree_model(row.iterchildren(), data, func)
        if func(row, data):
#            debug('row %s: %s' % (row, row[0]))
            try:
                results.extend(row.iter)
            except:
                results = [row.iter]
#    debug(results)
    return results



def clear_model(obj_with_model):
    '''
    and and remove the model on an object
    '''
    model = obj_with_model.get_model()
    if model is None:
        return

    ncols = model.get_n_columns()
    def del_cb(model, path, iter, data=None):
        for c in xrange(0, ncols):
            v =  model.get_value(iter, c)
            del v
        del iter
    model.foreach(del_cb)
    model.clear()
    del model
    model = None
    obj_with_model.set_model(None)


def combo_set_active_text(combo, value):
    '''
    does the same thing as set_combo_from_value but this looks more like a
    GTK+ method
    '''
    set_combo_from_value(combo, value)


def set_combo_from_value(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    find value in combo model and set it as active, else raise ValueError
    cmp(row, value) is the a function to use for comparison

    NOTE: if more than one value is found in the combo then the first one
    in the list is set
    '''
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        raise ValueError('set_combo_from_value() - could not find value in '\
                         'combo: %s' % value)
    combo.set_active_iter(matches[0])


def combo_get_value_iter(combo, value, cmp=lambda row, value: row[0] == value):
    '''
    @param combo: the combo where we should search
    @param value: the value to search for
    @param cmp: the method to use to compare rows in the combo model and value,
        the default is C{lambda row, value: row[0] == value}
    @return: the gtk.TreeIter that points to value

    NOTE: if more than one value is found in the combo then the first one
    in the list is returned
    '''
    model = combo.get_model()
    matches = search_tree_model(model, value, cmp)
    if len(matches) == 0:
        return None
    return matches[0]


def set_widget_value(glade_xml, widget_name, value, markup=True, default=None):
    '''
    @param glade_xml: the glade_file to get the widget from
    @param widget_name: the name of the widget
    @param value: the value to put in the widget
    @param markup: whether or not
    @param default: the default value to put in the widget if the value is None

    NOTE: any values passed in for widgets that expect a string will call
    the values __str__ method
    '''
    import gtk
    w = glade_xml.get_widget(widget_name)
    if value is None:  # set the value from the default
        if isinstance(w,(gtk.Label, gtk.TextView, gtk.Entry)) \
               and default is None:
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
            w.set_inconsistent(False)
            w.set_active(True)
        elif value is False: # how come i have to unset inconsistent for False?
            w.set_inconsistent(False)
            w.set_active(False)
        else:
            w.set_inconsistent(True)
    else:
        raise TypeError('utils.set_widget_value(): Don\'t know how to handle '
                        'the widget type %s with name %s' % \
                        (type(w), widget_name))

# TODO: if i escape the messages that come in then my own markup doesn't
# work, what really needs to be done is make sure that any exception that
# are going to be passed to one of these dialogs should be escaped before
# coming through

def create_message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK,
                          parent=None):
    '''
    '''
    icon = default_icon
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.gui.window
            icon = bauble.default_icon
        except:
            parent = None
    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                          parent=parent, type=type, buttons=buttons)
    d.set_title('Bauble')
    d.set_markup(msg)
    if d.get_icon() is None:
        pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
        d.set_icon(pixbuf)
        d.set_property('skip-taskbar-hint', False)
    d.show_all()
    return d


def message_dialog(msg, type=gtk.MESSAGE_INFO, buttons=gtk.BUTTONS_OK,
                   parent=None):
    '''
    '''
    d = create_message_dialog(msg, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def create_yes_no_dialog(msg, parent=None):
    '''
    '''
    icon = default_icon
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.gui.window
            icon = bauble.default_icon
        except:
            parent = None
    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         parent=parent, type=gtk.MESSAGE_QUESTION,
                         buttons = gtk.BUTTONS_YES_NO)
    d.set_title('Bauble')
    d.set_markup(msg)
    if d.get_icon() is None:
        pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
        d.set_icon(pixbuf)
        d.set_property('skip-taskbar-hint', False)
##     if sys.platform == "win32":
##         d.set_alternative_button_order([gtk.RESPONSE_YES, gtk.RESPONSE_NO])
    d.show_all()
    return d


# TODO: it would be nice to implement a yes_or_no method that asks from the
# console if there is no gui. is it possible to know if we have a terminal
# to write to?
def yes_no_dialog(msg, parent=None, yes_delay=-1):
    """
    @param msg: the message to display in the dialog
    @param parent: the dialog's parent
    @param yes_delay: the number of seconds before the yes button should
    become sensitive
    """
    d = create_yes_no_dialog(msg, parent)
    if yes_delay > 0:
        d.set_response_sensitive(gtk.RESPONSE_YES, False)
        def on_timeout():
            if d.get_property('visible'): # conditional avoids GTK+ warning
                d.set_response_sensitive(gtk.RESPONSE_YES, True)
            return False
        import gobject
        gobject.timeout_add(yes_delay*1000, on_timeout)
    r = d.run()
    d.destroy()
    return r == gtk.RESPONSE_YES

#
# TODO: give the button the default focus instead of the expander
#
def create_message_details_dialog(msg, details, type=gtk.MESSAGE_INFO,
                                  buttons=gtk.BUTTONS_OK, parent=None):
    '''
    '''
    icon = default_icon
    if parent is None:
        try: # this might get called before bauble has started
            parent = bauble.gui.window
            icon = bauble.default_icon
        except:
            parent = None


    d =gtk.MessageDialog(flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT,
                         parent=parent,type=type, buttons=buttons)
    d.set_title('Bauble')
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
    if d.get_icon() is None:
        pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
        d.set_icon(pixbuf)
        d.set_property('skip-taskbar-hint', False)

    d.show_all()
    return d


def message_details_dialog(msg, details, type=gtk.MESSAGE_INFO,
                           buttons=gtk.BUTTONS_OK, parent=None):
    '''
    '''
    d = create_message_details_dialog(msg, details, type, buttons, parent)
    r = d.run()
    d.destroy()
    return r


def utf8(obj):
    '''
    return a unicode object representation of obj
    '''
    return unicode(str(obj), 'utf-8')


def xml_safe(str, encoding='utf-8'):
    '''
    return a string with character entities escaped safe for xml, if the
    str paramater is a string a string is returned, if str is a unicode object
    then a unicode object is returned
    '''
    # what about encodings.string_escape to escape strings
    assert isinstance(str, basestring)
    if isinstance(str, unicode):
        return unicode(saxutils.escape(str.encode(encoding)), encoding)
    else:
        return saxutils.escape(str)


def xml_safe_utf8(obj):
    return xml_safe(utf8(obj))


__natsort_rx = re.compile('(\d+(?:\.\d+)?)')

def natsort_key(obj):
    """
    a key getter for sort and sorted function

    the sorting is done on return value of obj.__str__() so we can sort
    objects as well, i don't know if this will cause problems with unicode

    use like: sorted(some_list, key=utils.natsort_key)
    """
    item = str(obj)
    chunks = __natsort_rx.split(item)
    for ii in range(len(chunks)):
        if chunks[ii] and chunks[ii][0] in '0123456789':
            if '.' in chunks[ii]:
                numtype = float
            else:
                numtype = int
            # wrap in tuple with '0' to explicitly specify numbers come first
            chunks[ii] = (0, numtype(chunks[ii]))
        else:
            chunks[ii] = (1, chunks[ii])
    return (chunks, item)



def delete_or_expunge(obj):
    """
    If the object is in object_session(obj).new then expunge it from the
    session.  If not then session.delete it.
    """
    from sqlalchemy.orm import object_session
    session = object_session(obj)
    if session is None:
        return
    if obj in session.new:
#        debug('expunge obj: %s -- %s' % (obj, repr(obj)))
        session.expunge(obj)
        del obj
    else:
#        debug('delete obj: %s -- %s' % (obj, repr(obj)))
        session.delete(obj)


def chunk(iterable, n):
    '''
    return iterable in chunks of size n
    '''
    # TODO: this could probably be implemented way more efficiently,
    # maybe using itertools
    chunk = []
    ctr = 0
    for it in iterable:
        chunk.append(it)
        ctr += 1
        if ctr >= n:
            yield chunk
            chunk = []
            ctr = 0
    yield chunk


def reset_sequence(column):
    """
    if column.sequence is not None or the column is an Integer and
    column.autoincrement is true then reset the sequence for the next
    available value for the column...if the column doesn't have a
    sequence then do nothing and return

    The SQL statements are executed directly from bauble.engine
    """
    import bauble
    from sqlalchemy.types import Integer
    from sqlalchemy import schema
    if bauble.engine.name in ('sqlite', 'mysql'):
        pass # sqlite and mysql seem to work fine
    elif bauble.engine.name == 'postgres':
        sequence_name = None
        # this crazy elif conditional is from
        # sqlalchemy.database.postgres.PGDefaultRunner
        if hasattr(column, "sequence") and column.sequence is not None:
            sequence_name = column.sequence.name
        elif (isinstance(column.type, Integer) and column.autoincrement) and (column.default is None or (isinstance(column.default, schema.Sequence) and column.default.optional)) and len(column.foreign_keys)==0:
            sequence_name = '%s_%s_seq' %(column.table.name, column.name)
        else:
            return
        stmt = "SELECT max(%s) from %s" % (column.name, column.table.name)

        maxid = bauble.engine.execute(stmt).fetchone()[0]
        if maxid == None:
            stmt = "SELECT setval('%s', 1);" % (sequence_name)
        else:
            stmt = "SELECT setval('%s', max(%s)+1) from %s;" \
                   % (sequence_name, column.name, column.table.name)
        bauble.engine.execute(stmt)
    else:
        raise NotImplementedError(_('Error: using sequences hasn\'t been '\
                                    'tested on this database type: %s' % \
                                    bauble.engine.name))

# TODO: always req month and year, day can be optional, what about a
# flag to make the day optional, like?
def date_to_str(date, format):
    """
    @param data: a datetime object
    @param format: the format of the string to return, uses:
    yyyy,yy,d,dd,m,mm

    We don't do any validation that the format is correct or invalid
    """
    import re
    s = format.replace('yyyy', str(date.year))
    month = date.month
    if month < 10:
        month = '0%s' % month
    s = s.replace('mm', str(month))
    s = s.replace('m', str(date.month))
    day = date.day
    if day < 10:
        day = '0%s' % day
    s = s.replace('dd', str(day))
    s = s.replace('d', str(date.day))
    return s


