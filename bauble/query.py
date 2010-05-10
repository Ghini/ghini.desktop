import gtk
import pyparsing
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.properties import *

import bauble
import bauble.view as view
import bauble.db as db
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug
import bauble.utils as utils

class SchemaBrowser(gtk.VBox):


    def __init__(self, *args, **kwargs):
        super(SchemaBrowser, self).__init__(*args, **kwargs)
        self.props.spacing = 10
        # WARNING: this is a hack from bauble.view.MapperSearch
        self.domain_map = {}
        self.domain_map = view.MapperSearch.get_domain_classes().copy()

        frame = gtk.Frame(_("Search Domain"))
        self.pack_start(frame, expand=False, fill=False)
        self.table_combo = gtk.combo_box_new_text()
        frame.add(self.table_combo)
        for key in self.domain_map.keys():
            self.table_combo.append_text(key)

        self.table_combo.connect('changed', self.on_table_combo_changed)

        self.prop_tree = gtk.TreeView()
        self.prop_tree.set_headers_visible(False)
        cell = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Property"), cell)
        self.prop_tree.append_column(column)
        column.add_attribute(cell, 'text', 0)

        self.prop_tree.connect('test_expand_row', self.on_row_expanded)

        frame = gtk.Frame(_('Domain Properties'))
        sw = gtk.ScrolledWindow()
        sw.add(self.prop_tree)
        frame.add(sw)
        self.pack_start(frame, expand=True, fill=True)


    def _insert_props(self, mapper, model, treeiter):
        """
        Insert the properties from mapper into the model at treeiter
        """
        column_properties = sorted(filter(lambda x:  \
                                              isinstance(x, ColumnProperty) \
                                              and not x.key.startswith('_'),
                                          mapper.iterate_properties),
                                   key=lambda k: k.key)
        for prop in column_properties:
            model.append(treeiter, [prop.key, prop])


        relation_properties = sorted(filter(lambda x:  \
                                                isinstance(x, RelationProperty)\
                                              and not x.key.startswith('_'),
                                          mapper.iterate_properties),
                                   key=lambda k: k.key)
        for prop in relation_properties:
            it = model.append(treeiter, [prop.key, prop])
            model.append(it, ['', None])


    def on_row_expanded(self, treeview, treeiter, path):
        """
        Called before the row is expanded and populates the children of the row.
        """
        debug('on_row_expanded')
        model = treeview.props.model
        parent = treeiter
        while model.iter_has_child(treeiter):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids-1)
            model.remove(child)

        # prop should always be a RelationProperty
        prop = treeview.props.model[treeiter][1]
        self._insert_props(prop.mapper, model, treeiter)


    def on_table_combo_changed(self, combo, *args):
        """
        Change the table to use for the query
        """
        utils.clear_model(self.prop_tree)
        it = combo.get_active_iter()
        domain = combo.props.model[it][0]
        mapper = class_mapper(self.domain_map[domain])
        model = gtk.TreeStore(str, object)
        root = model.get_iter_root()
        self._insert_props(mapper, model, root)
        self.prop_tree.props.model = model



class QueryBuilder(object):

    def __init__(self, *args, **kwargs):
        pass


    def on_table_combo_changed(self, combo, *args):
        # TODO: warn that the current buffer contents will be destroyed
        self.buffer.set_text('') # clear the buffer first
        self.insert_text('%s where ' % combo.get_active_text())


    def on_prop_row_activated(self, treeview, path, column):
        model = treeview.props.model
        it = model.get_iter(path)
        if model.iter_has_child(it):
            return
        parts = []
        # walk down the path getting the strings for each level
        for n in xrange(0, len(path)):
            parts.append(model[path[0:n+1]][0])
        self.insert_text('.'.join(parts))


    def get_query(self):
        return self.buffer.props.text


    def start(self):
        parent = None
        if bauble.gui and bauble.gui.window:
            parent = bauble.gui.window
        self.dialog = gtk.Dialog(_("Query Builder"), parent,
                              gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                      (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                  gtk.STOCK_OK, gtk.RESPONSE_OK))
        self.dialog.set_response_sensitive(gtk.RESPONSE_OK, False)
        self.dialog.vbox.props.spacing = 10
        hbox = gtk.HBox()
        hbox.props.spacing = 20
        self.dialog.vbox.pack_start(hbox, expand=False, fill=False)
        self.schema_browser = SchemaBrowser()
        self.schema_browser.set_size_request(-1, 200)
        self.schema_browser.prop_tree.\
            connect('row_activated', self.on_prop_row_activated)

        self.schema_browser.table_combo.\
            connect('changed', self.on_table_combo_changed)
        hbox.pack_start(self.schema_browser)

        table = gtk.Table(rows=3, columns=3)
        vbox = gtk.VBox()
        vbox.props.spacing = 30
        vbox.pack_start(table, expand=False, fill=False)
        hbox.pack_start(vbox, expand=False, fill=False)

        operators = ['=', '!=', '<', '<=', '>', '>=', 'like']
        row = 0
        column = 0
        for op in operators:
            b = gtk.Button(op)
            def insert_op(text):
                self.insert_text(' %s "" ' % text)
                # move cursor between the inserted quotes
                position = self.buffer.props.cursor_position
                it = self.buffer.get_iter_at_offset(position)
                it.backward_cursor_positions(2)
                self.buffer.place_cursor(it)
            b.connect('clicked', lambda w, o: insert_op(o), op)
            table.attach(b, column, column+1, row, row+1)
            if column % 3 == 2:
                row += 1
                column = 0
            else:
                column += 1

        table = gtk.Table(rows=1, columns=2)
        vbox.pack_start(table, expand=False, fill=False)
        operators = ['and', 'or']
        row = 0
        column = 0
        for op in operators:
            b = gtk.Button(op)
            b.connect('clicked', lambda x: self.insert_text(' %s ' % op))
            table.attach(b, column, column+1, row, row+1)
            column += 1

        frame = gtk.Frame(_('Query'))
        self.dialog.vbox.pack_start(frame)

        self.buffer = gtk.TextBuffer()
        self.buffer.connect('changed', self.on_buffer_changed)
        self.text_view = gtk.TextView(self.buffer)
        self.text_view.set_size_request(400, 150)
        frame.add(self.text_view)

        self.dialog.vbox.show_all()
        self.dialog.run()
        self.dialog.hide()


    def on_buffer_changed(self, buffer):
        # if SearchParser.query doesn't validate the string then make
        # the OK button insensitive
        sensitive = True
        try:
            view.SearchParser.query.parseString(self.buffer.props.text)
        except pyparsing.ParseException, e:
            #debug(e)
            sensitive = False
        self.dialog.set_response_sensitive(gtk.RESPONSE_OK, sensitive)


    def insert_text(self, text):
        self.buffer.insert_at_cursor(text)
        self.text_view.grab_focus()



if __name__ == '__main__':
    import bauble.test
    uri = 'sqlite:///:memory:'
    bauble.test.init_bauble(uri)
    qb = QueryBuilder()
    qb.start()
