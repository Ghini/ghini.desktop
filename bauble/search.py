import gtk
from pyparsing import *
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.orm.properties import *

import bauble
from bauble.error import check, CheckConditionError, BaubleError
import bauble.db as db
import bauble.pluginmgr as pluginmgr
from bauble.utils.log import debug
import bauble.utils as utils


def search(text, session):
    results = set()
    for strategy in _search_strategies:
        results.update(strategy.search(text, session))
    return list(results)



class SearchParser(object):
    """
    The parser for bauble.search.MapperSearch
    """
    value_chars = Word(alphanums + '%.-_*;:')
    # value can contain any string once its quoted
    value = value_chars | quotedString.setParseAction(removeQuotes)
    value_list = (value ^ delimitedList(value) ^ OneOrMore(value))
    binop = oneOf('= == != <> < <= > >= not like contains has ilike '\
                  'icontains ihas is')('binop')
    domain = Word(alphas, alphanums)('domain')
    domain_values = Group(value_list.copy())
    domain_expression = (domain + Literal('=') + Literal('*') + StringEnd()) \
                        | (domain + binop + domain_values + StringEnd())

    and_token = CaselessKeyword('and')
    or_token = CaselessKeyword('or')
    log_op = and_token | or_token

    identifier = Group(delimitedList(Word(alphas, alphanums+'_'), '.'))
    ident_expression = Group(identifier + binop + value)
    query_expression = ident_expression \
                       + ZeroOrMore(log_op + ident_expression)
    query = domain + CaselessKeyword('where').suppress() \
            + Group(query_expression) + StringEnd()

    statement = query | domain_expression | value_list


    def parse_string(self, text):
        '''
        returns a pyparsing.ParseResults objects that represents either a
        query, an expression or a list of values
        '''
        return self.statement.parseString(text)



class SearchStrategy(object):
    """
    Interface for adding search strategies to a view.
    """

    def search(self, text, session):
        '''
        :param text: the search string
        :param: the session to use for the search

        Return an iterator that iterates over mapped classes retrieved
        from the search.
        '''
        pass



class MapperSearch(SearchStrategy):

    """
    Mapper Search support three types of search expression:
    1. value searches: search that are just list of values, e.g. value1,
    value2, value3, searches all domains and registered columns for values
    2. expression searches: searched of the form domain=value, resolves the
    domain and searches specific columns from the mapping
    3. query searchs: searches of the form domain where ident.ident = value,
    resolve the domain and identifiers and search for value
    """

    _domains = {}
    _shorthand = {}
    _properties = {}

    def __init__(self):
        super(MapperSearch, self).__init__()
        self._results = set()
        self.parser = SearchParser()


    def add_meta(self, domain, cls, properties):
        """
        Adds search meta to the domain

        :param domain: a string, list or tuple of domains that will resolve
        to cls a search string, domain act as a shorthand to the class name
        :param cls: the class the domain will resolve to
        :param properties: a list of string names of the properties to
        search by default
        """
        check(isinstance(properties, list), _('MapperSearch.add_meta(): '\
        'default_columns argument must be list'))
        check(len(properties) > 0, _('MapperSearch.add_meta(): '\
        'default_columns argument cannot be empty'))
        if isinstance(domain, (list, tuple)):
            self._domains[domain[0]] = cls, properties
            for d in domain[1:]:
                self._shorthand[d] = domain[0]
        else:
            self._domains[d] = cls, properties
        self._properties[cls] = properties


    @classmethod
    def get_domain_classes(cls):
        d = {}
        for domain, item in cls._domains.iteritems():
            d.setdefault(domain, item[0])
        return d

    def on_query(self, s, loc, tokens):
        """
        Called when the parser hits a query token.

        Queries can use more database specific features.  This also
        means that the same query might not work the same on different
        database types. For example, on a PostgreSQL database you can
        use ilike but this would raise an error on SQLite.
        """
        # The method requires that the underlying database support
        # union and intersect. At the time of writing this MySQL
        # didn't.

        # TODO: support 'not' a boolean op as well, e.g sp where
        # genus.genus=Maxillaria and not genus.family=Orchidaceae
        domain, expr = tokens
        check(domain in self._domains or domain in self._shorthand,
              'Unknown search domain: %s' % domain)
        if domain in self._shorthand:
            domain = self._shorthand[domain]
        cls = self._domains[domain][0]
        main_query = self._session.query(cls)
        mapper = class_mapper(cls)
        expr_iter = iter(expr)
        boolop = None
        for e in expr_iter:
            idents, cond, val = e
            # debug('cls: %s, idents: %s, cond: %s, val: %s'
            #       % (cls.__name__, idents, cond, val))
            if val == 'None':
                val = None
            if cond == 'is':
                cond = '='
            elif cond == 'is not':
                cond = '!='
            elif cond in ('ilike', 'icontains', 'ihas'):
                cond = lambda col: \
                    lambda val: utils.ilike(col, '%s' % val)


            if len(idents) == 1:
                # we get here when the idents only refer to a property
                # on the mapper table..i.e. a column
                col = idents[0]
                msg = _('The %(tablename)s table does not have a '\
                       'column named "%(columname)s"') % \
                       dict(tablename=mapper.local_table.name,
                            columname=col)
                check(col in mapper.c, msg)
                if isinstance(cond, str):
                    clause = getattr(cls, col).op(cond)(utils.utf8(val))
                else:
                    clause = cond(getattr(cls, col))(utils.utf8(val))
                query = self._session.query(cls).filter(clause).order_by(None)
            else:
                # we get here when the idents refer to a relation on a
                # mapper/table
                relations = idents[:-1]
                col = idents[-1]
                query = self._session.query(cls)
                query = query.join(relations)
                if isinstance(cond, str):
                    clause = query._joinpoint.c[col].op(cond)(utils.utf8(val))
                else:
                    clause = cond(query._joinpoint.c[col])(utils.utf8(val))
                query = query.filter(clause).order_by(None)

            if boolop == 'or':
                main_query = main_query.union(query)
            elif boolop == 'and':
                main_query = main_query.intersect(query)
            else:
                main_query = query

            try:
                boolop = expr_iter.next()
            except StopIteration:
                pass

        self._results.update(main_query.order_by(None).all())


    def on_domain_expression(self, s, loc, tokens):
        """
        Called when the parser hits a domain_expression token.

        Searching using domain expressions is a little more magical
        and queries mapper properties that were passed to add_meta()

        To do a case sensitive search for a specific string use the
        double equals, '=='
        """
        domain, cond, values = tokens
        try:
            if domain in self._shorthand:
                domain = self._shorthand[domain]
            cls, properties = self._domains[domain]
        except KeyError:
            raise KeyError(_('Unknown search domain: %s' % domain))

	query = self._session.query(cls)

	# select all objects from the domain
        if values == '*':
            self._results.update(query.all())
            return

        mapper = class_mapper(cls)

        if cond in ('like', 'ilike', 'contains', 'icontains', 'has', 'ihas'):
            condition = lambda col: \
                lambda val: utils.ilike(mapper.c[col], '%%%s%%' % val)
        elif cond == '=':
            condition = lambda col: \
                lambda val: utils.ilike(mapper.c[col], utils.utf8(val))
        else:
            condition = lambda col: \
                lambda val: mapper.c[col].op(cond)(val)

        for col in properties:
            ors = or_(*map(condition(col), values))
            self._results.update(query.filter(ors).all())
        return tokens


    def on_value_list(self, s, loc, tokens):
        """
        Called when the parser hits a value_list token

        Search with a list of values is the broadest search and
        searches all the mapper and the properties configured with
        add_meta()
        """
        # debug('values: %s' % tokens)
        # debug('  s: %s' % s)
        # debug('  loc: %s' % loc)
        # debug('  toks: %s' % tokens)

        # make searches case-insensitive, in postgres use ilike,
        # in other use upper()
        like = lambda table, col, val: \
            utils.ilike(table.c[col], ('%%%s%%' % val))

        for cls, columns in self._properties.iteritems():
            q = self._session.query(cls)
            cv = [(c,v) for c in columns for v in tokens]
            # as of SQLAlchemy>=0.4.2 we convert the value to a unicode
            # object if the col is a Unicode or UnicodeText column in order
            # to avoid the "Unicode type received non-unicode bind param"
            def unicol(col, v):
                mapper = class_mapper(cls)
                if isinstance(mapper.c[col].type, (Unicode,UnicodeText)):
                    return unicode(v)
                else:
                    return v
            mapper = class_mapper(cls)
            q = q.filter(or_(*[like(mapper, c, unicol(c, v)) for c,v in cv]))
            self._results.update(q.all())


    def search(self, text, session):
        """
        Returns a set() of database hits for the text search string.

        If session=None then the session should be closed after the results
        have been processed or it is possible that some database backends
        could cause deadlocks.
        """
        self._session = session

        # this looks kinda ridiculous to add the parse actions and
        # then remove them but then it allows us to reuse the parser
        # for other things, particulary tests, without calling the
        # parse actions
        self.parser.query.setParseAction(self.on_query)
        self.parser.domain_expression.setParseAction(self.on_domain_expression)
        self.parser.value_list.setParseAction(self.on_value_list)

        self._results.clear()
        self.parser.parse_string(text)

        self.parser.query.parseAction = []
        self.parser.domain_expression.parseAction = []
        self.parser.value_list.parseAction = []

        # these results get filled in when the parse actions are called
        return self._results


"""
the search strategy is keyed by domain and each value will be a list of
SearchStrategy instances
    """
_search_strategies = [MapperSearch()]

def add_strategy(strategy):
    _search_strategies.append(strategy())


def get_strategy(name):
    for strategy in _search_strategies:
        if strategy.__class__.__name__ == name:
            return strategy


class SchemaBrowser(gtk.VBox):


    def __init__(self, *args, **kwargs):
        super(SchemaBrowser, self).__init__(*args, **kwargs)
        self.props.spacing = 10
        # WARNING: this is a hack from MapperSearch
        self.domain_map = {}
        self.domain_map = MapperSearch.get_domain_classes().copy()

        frame = gtk.Frame(_("Search Domain"))
        self.pack_start(frame, expand=False, fill=False)
        self.table_combo = gtk.combo_box_new_text()
        frame.add(self.table_combo)
        for key in sorted(self.domain_map.keys()):
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



# class QueryBuilder2(object):

#     def __init__(self, *args, **kwargs):
#         pass


#     def on_table_combo_changed(self, combo, *args):
#         # TODO: warn that the current buffer contents will be destroyed
#         self.buffer.set_text('') # clear the buffer first
#         self.insert_text('%s where ' % combo.get_active_text())


#     def on_prop_row_activated(self, treeview, path, column):
#         model = treeview.props.model
#         it = model.get_iter(path)
#         if model.iter_has_child(it):
#             return
#         parts = []
#         # walk down the path getting the strings for each level
#         for n in xrange(0, len(path)):
#             parts.append(model[path[0:n+1]][0])
#         self.insert_text('.'.join(parts))


#     def get_query(self):
#         return self.buffer.props.text


#     def start(self):
#         parent = None
#         if bauble.gui and bauble.gui.window:
#             parent = bauble.gui.window
#         self.dialog = gtk.Dialog(_("Query Builder"), parent,
#                               gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
#                       (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
#                                   gtk.STOCK_OK, gtk.RESPONSE_OK))
#         self.dialog.set_response_sensitive(gtk.RESPONSE_OK, False)
#         self.dialog.vbox.props.spacing = 10
#         hbox = gtk.HBox()
#         hbox.props.spacing = 20
#         self.dialog.vbox.pack_start(hbox, expand=False, fill=False)
#         self.schema_browser = SchemaBrowser()
#         self.schema_browser.set_size_request(-1, 200)
#         self.schema_browser.prop_tree.\
#             connect('row_activated', self.on_prop_row_activated)

#         self.schema_browser.table_combo.\
#             connect('changed', self.on_table_combo_changed)
#         hbox.pack_start(self.schema_browser)

#         table = gtk.Table(rows=3, columns=3)
#         vbox = gtk.VBox()
#         vbox.props.spacing = 30
#         vbox.pack_start(table, expand=False, fill=False)
#         hbox.pack_start(vbox, expand=False, fill=False)

#         operators = ['=', '!=', '<', '<=', '>', '>=', 'like']
#         row = 0
#         column = 0
#         for op in operators:
#             b = gtk.Button(op)
#             def insert_op(text):
#                 self.insert_text(' %s "" ' % text)
#                 # move cursor between the inserted quotes
#                 position = self.buffer.props.cursor_position
#                 it = self.buffer.get_iter_at_offset(position)
#                 it.backward_cursor_positions(2)
#                 self.buffer.place_cursor(it)
#             b.connect('clicked', lambda w, o: insert_op(o), op)
#             table.attach(b, column, column+1, row, row+1)
#             if column % 3 == 2:
#                 row += 1
#                 column = 0
#             else:
#                 column += 1

#         table = gtk.Table(rows=1, columns=2)
#         vbox.pack_start(table, expand=False, fill=False)
#         operators = ['and', 'or']
#         row = 0
#         column = 0
#         for op in operators:
#             b = gtk.Button(op)
#             b.connect('clicked', lambda x: self.insert_text(' %s ' % op))
#             table.attach(b, column, column+1, row, row+1)
#             column += 1

#         frame = gtk.Frame(_('Query'))
#         self.dialog.vbox.pack_start(frame)

#         self.buffer = gtk.TextBuffer()
#         self.buffer.connect('changed', self.on_buffer_changed)
#         self.text_view = gtk.TextView(self.buffer)
#         self.text_view.set_size_request(400, 150)
#         frame.add(self.text_view)

#         self.dialog.vbox.show_all()
#         r = self.dialog.run()
#         self.dialog.hide()
#         return r


#     def on_buffer_changed(self, buffer):
#         # if SearchParser.query doesn't validate the string then make
#         # the OK button insensitive
#         sensitive = True
#         try:
#             view.SearchParser.query.parseString(self.buffer.props.text)
#         except pyparsing.ParseException, e:
#             #debug(e)
#             sensitive = False
#         self.dialog.set_response_sensitive(gtk.RESPONSE_OK, sensitive)


#     def insert_text(self, text):
#         self.buffer.insert_at_cursor(text)
#         self.text_view.grab_focus()


class SchemaMenu(gtk.Menu):

    def __init__(self, mapper, activate_cb=None):
        """
        :param mapper:
        """
        super(SchemaMenu, self).__init__()
        self.activate_cb = activate_cb
        map(self.append, self._get_prop_menuitems(mapper))
        self.show_all()



    def on_activate(self, menuitem):
        """
        Call when menu items that hold column properties are activated
        """
        path = []
        path = [menuitem.get_child().props.label]
        menu = menuitem.get_parent()
        while menu is not None:
            menuitem = menu.props.attach_widget
            if not menuitem:
                break
            label = menuitem.props.label
            path.append(label)
            menu = menuitem.get_parent()
        full_path = '.'.join(reversed(path))
        self.activate_cb(self, menuitem, full_path)


    def on_select(self, menuitem, prop):
        """
        Called when menu items that have submenus are selected
        """

        submenu = menuitem.get_submenu()
        if len(submenu.get_children()) == 0:
            map(submenu.append, self._get_prop_menuitems(prop.mapper))
        submenu.show_all()



    def _get_prop_menuitems(self, mapper):
        items = []
        column_properties = sorted(filter(lambda x:  \
                                              isinstance(x, ColumnProperty) \
                                              and not x.key.startswith('_'),
                                          mapper.iterate_properties),
                                   key=lambda k: k.key)

        for prop in column_properties:
            item = gtk.MenuItem(prop.key)
            item.props.use_underline = False
            item.connect('activate', self.on_activate)
            items.append(item)

        relation_properties = sorted(filter(lambda x:  \
                                                isinstance(x, RelationProperty)\
                                              and not x.key.startswith('_'),
                                          mapper.iterate_properties),
                                   key=lambda k: k.key)
        for prop in relation_properties:
            item = gtk.MenuItem(prop.key)
            item.props.use_underline = False
            items.append(item)
            submenu = gtk.Menu()
            item.set_submenu(submenu)
            item.connect('select', self.on_select, prop)
        return items



class ExpressionRow(gtk.HBox):

    def __init__(self, mapper, show_and_or_combo=True):
        """
        :param mapper:
        """
        super(ExpressionRow, self).__init__()
        self.props.spacing = 10

        self.and_or_combo = None
        if show_and_or_combo:
            self.and_or_combo = gtk.combo_box_new_text()
            self.and_or_combo.append_text("and")
            self.and_or_combo.append_text("or")
            self.and_or_combo.set_active(0)
            self.pack_start(self.and_or_combo)

        self.prop_button = gtk.Button(_('Choose a property...'))
        self.prop_button.props.use_underline = False
        def on_prop_button_clicked(button, event, menu):
            menu.popup(None, None, None, event.button, event.time)
        def menu_activated(menu, menuitem, path):
            self.prop_button.props.label = path
        self.schema_menu = SchemaMenu(mapper, menu_activated)
        self.prop_button.connect('button-press-event', on_prop_button_clicked,
                            self.schema_menu)
        self.pack_start(self.prop_button)

        self.cond_combo = gtk.combo_box_new_text()
        conditions = ['=', '==', '!=', '<',
                      '<=', '>', '>=', 'is', 'is not', 'like', 'ilike']
        map(self.cond_combo.append_text, conditions)
        self.pack_start(self.cond_combo)

        self.value_entry = gtk.Entry()
        self.pack_start(self.value_entry)

        self.show_all()


    def get_expression(self):
        """

        :param self:
        """
        return ' '.join([self.prop_button.props.label,
                         self.cond_combo.get_active_text(),
                         self.value_entry.props.text])



class QueryBuilder(gtk.Dialog):

    def __init__(self, parent=None):
        """
        """
        super(QueryBuilder, self).\
            __init__(title=_("Query Builder"), parent=parent,
                     flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                     buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                              gtk.STOCK_OK, gtk.RESPONSE_OK))

        self.vbox.props.spacing = 15
        self.expression_rows = []
        self.mapper = None
        self._first_choice = True


    def on_domain_combo_changed(self, *args):
        """
        """
        if self._first_choice:
            self.domain_combo.remove_text(0)
            self._first_choice = False

        # TODO: each time its changed we should remove all the expression
        # row and add one to the top
        self.expressions_vbox.props.sensitive = True
        self.add_expression_row(show_and_or_combo=False)


    def validate(self):
        """
        Validate the search expression is a valid expression.
        """
        return True


    def add_expression_row(self, show_and_or_combo=True):
        domain = self.domain_map[self.domain_combo.get_active_text()]
        self.mapper = class_mapper(domain)
        row = ExpressionRow(self.mapper, show_and_or_combo=show_and_or_combo)
        self.expression_rows.append(row)
        self.expressions_vbox.pack_start(row)
        self.expressions_vbox.show_all()


    def start(self):
        self.domain_map = {}
        self.domain_map = MapperSearch.get_domain_classes().copy()

        frame = gtk.Frame(_("Search Domain"))
        self.vbox.pack_start(frame, expand=False, fill=False)
        self.domain_combo = gtk.combo_box_new_text()
        frame.add(self.domain_combo)
        for key in sorted(self.domain_map.keys()):
            self.domain_combo.append_text(key)
        self.domain_combo.insert_text(0, _("Choose a search domain..."))
        self.domain_combo.set_active(0)

        self.domain_combo.connect('changed', self.on_domain_combo_changed)

        frame = gtk.Frame(_("Expressions"))
        self.expressions_vbox = gtk.VBox()
        self.expressions_vbox.props.spacing = 5
        frame.add(self.expressions_vbox)
        self.vbox.pack_start(frame)

        add_button = gtk.Button()
        img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
        add_button.props.image = img
        add_button.connect("clicked", lambda w: self.add_expression_row())
        align = gtk.Alignment(0, 0, 0, 0)
        align.add(add_button)
        self.expressions_vbox.pack_end(align, fill=False, expand=False)
        #self.expressions_vbox.pack_end(add_button, fill=False, expand=False)

        # made sensitive when a search domain is first chosen
        self.expressions_vbox.props.sensitive = False

        self.vbox.show_all()
        self.run()



    def get_query(self):
        """
        Return query expression string.
        """
        domain = self.domain_combo.get_active_text()
        debug(domain)
        debug('where')
        for row in self.expression_rows:
            debug(row.get_expression())


if __name__ == '__main__':
    import bauble.test
    uri = 'sqlite:///:memory:'
    bauble.test.init_bauble(uri)
    qb = QueryBuilder()
    qb.start()
    debug(qb.get_query())

