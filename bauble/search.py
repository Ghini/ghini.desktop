import weakref

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

# TODO: remove date columns from searches

# TODO: show list of completions of valid values, maybe even create
# combos for enum types values instead of text entries

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
        :param session: the session to use for the search

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



class SchemaMenu(gtk.Menu):
    """
    SchemaMenu

    :param mapper:
    :param activate cb:
    :param relation_filter:
    """

    def __init__(self, mapper, activate_cb=None, relation_filter=lambda p:True):
        super(SchemaMenu, self).__init__()
        self.activate_cb = activate_cb
        self.relation_filter = relation_filter
        map(self.append, self._get_prop_menuitems(mapper))
        self.show_all()


    def on_activate(self, menuitem, prop):
        """
        Call when menu items that hold column properties are activated.
        """
        path = []
        path = [menuitem.get_child().props.label]
        menu = menuitem.get_parent()
        while menu is not None:
            menuitem = menu.props.attach_widget
            if not menuitem:
                break
            label = menuitem.get_child().props.label
            path.append(label)
            menu = menuitem.get_parent()
        full_path = '.'.join(reversed(path))
        self.activate_cb(menuitem, full_path, prop)


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
            if not self.relation_filter(prop):
                continue
            item = gtk.MenuItem(prop.key, use_underline=False)
            item.connect('activate', self.on_activate, prop)
            items.append(item)

        # filter out properties that start with underscore since they
        # are considered private
        relation_properties = sorted(filter(lambda x:  \
                                                isinstance(x, RelationProperty)\
                                              and not x.key.startswith('_'),
                                          mapper.iterate_properties),
                                   key=lambda k: k.key)
        for prop in relation_properties:
            if not self.relation_filter(prop):
                continue
            item = gtk.MenuItem(prop.key, use_underline=False)
            items.append(item)
            submenu = gtk.Menu()
            item.set_submenu(submenu)
            item.connect('select', self.on_select, prop)
        return items



class ExpressionRow(object):
    """
    """

    def __init__(self, query_builder, remove_callback, row_number=None):
        self.mapper = weakref.proxy(query_builder.mapper)
        self.table = weakref.proxy(query_builder.expressions_table)
        self.dialog = weakref.proxy(query_builder)
        self.menu_item_selected = False
        if row_number is None:
            # assume we want the row appended to the end of the table
            row_number = self.table.props.n_rows

        self.and_or_combo = None
        if row_number != 1:
            self.and_or_combo = gtk.combo_box_new_text()
            self.and_or_combo.append_text("and")
            self.and_or_combo.append_text("or")
            self.and_or_combo.set_active(0)
            self.table.attach(self.and_or_combo, 0, 1, row_number, row_number+1)

        self.prop_button = gtk.Button(_('Choose a property...'))
        self.prop_button.props.use_underline = False
        def on_prop_button_clicked(button, event, menu):
            menu.popup(None, None, None, event.button, event.time)
        self.schema_menu = SchemaMenu(self.mapper,
                                      self.on_schema_menu_activated,
                                      self.relation_filter)
        self.prop_button.connect('button-press-event', on_prop_button_clicked,
                            self.schema_menu)
        self.table.attach(self.prop_button, 1, 2, row_number, row_number+1)

        self.cond_combo = gtk.combo_box_new_text()
        conditions = ['=', '!=', '<', '<=', '>', '>=', 'is', 'is not', 'like',
                      'ilike']
        map(self.cond_combo.append_text, conditions)
        self.cond_combo.set_active(0)
        self.table.attach(self.cond_combo, 2, 3, row_number, row_number+1)

        # by default we start with an entry but value_widget can
        # change depending on the type of the property chosen in the
        # schema menu, see self.on_schema_menu_activated
        self.value_widget = gtk.Entry()
        self.value_widget.connect('changed', self.on_value_changed)
        self.table.attach(self.value_widget, 3, 4, row_number, row_number+1)

        if row_number != 1:
            image = gtk.image_new_from_stock(gtk.STOCK_REMOVE,
                                             gtk.ICON_SIZE_BUTTON)
            self.remove_button = gtk.Button()
            self.remove_button.props.image = image
            self.remove_button.connect('clicked',
                                       lambda b: remove_callback(self))
            self.table.attach(self.remove_button, 4, 5, row_number,row_number+1)


    def on_value_changed(self, widget, *args):
        """
        Call the QueryBuilder.validate() for this row.
        Set the sensitivity of the gtk.RESPONSE_OK button on the QueryBuilder.
        """
        self.dialog.validate()


    def on_schema_menu_activated(self, menuitem, path, prop):
        """
        Called when an item in the schema menu is activated
        """
        self.prop_button.props.label = path
        self.menu_item_activated = True
        top = self.table.child_get_property(self.value_widget, 'top-attach')
        bottom = self.table.child_get_property(self.value_widget,
                                               'bottom-attach')
        right = self.table.child_get_property(self.value_widget, 'right-attach')
        left = self.table.child_get_property(self.value_widget, 'left-attach')
        self.table.remove(self.value_widget)

        # change the widget depending on the type of the selected property
        if isinstance(prop.columns[0].type, bauble.types.Enum):
            self.value_widget = gtk.ComboBox()
            cell = gtk.CellRendererText()
            self.value_widget.pack_start(cell, True)
            self.value_widget.add_attribute(cell, 'text', 1)
            model = gtk.ListStore(str, str)
            if prop.columns[0].type.translations:
                trans = prop.columns[0].type.translations
                prop_values = [(k,trans[k]) for k in sorted(trans.keys())]
            else:
                values = prop.columns[0].type.values
                prop_values = [(v,v) for v in sorted(values)]
            for value, translation in prop_values:
                model.append([value, translation])
            self.value_widget.props.model = model
            self.value_widget.connect('changed', self.on_value_changed)
        elif not isinstance(self.value_widget, gtk.Entry):
            self.value_widget = gtk.Entry()
            self.value_widget.connect('changed', self.on_value_changed)

        self.table.attach(self.value_widget, left, right, top, bottom)
        self.table.show_all()
        self.dialog.validate()


    def relation_filter(self, prop):
        if isinstance(prop, ColumnProperty) and \
                isinstance(prop.columns[0].type, bauble.types.Date):
            return False
        return True


    def get_widgets(self):
        """
        Returns a tuple of the and_or_combo, prop_button, cond_combo,
        value_widget, and remove_button widgets.
        """
        return self.and_or_combo, self.prop_button, self.cond_combo, \
            self.value_widget, self.remove_button


    def get_expression(self):
        """
        Return the expression represented but this ExpressionRow.  If
        the expression is not valid then return None.

        :param self:
        """

        if not self.menu_item_activated:
            return None

        value = ''
        if isinstance(self.value_widget, gtk.ComboBox):
            model = self.value_widget.props.model
            active_iter = self.value_widget.get_active_iter()
            if active_iter:
                value = model[active_iter][0]
        else:
            # assume its a gtk.Entry or other widget with a text property
            value = self.value_widget.props.text.strip()
        and_or = ''
        if self.and_or_combo:
            and_or = self.and_or_combo.get_active_text()
        return ' '.join([and_or, self.prop_button.props.label,
                         self.cond_combo.get_active_text(),
                         '"%s"' % value]).strip()



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
        self.set_response_sensitive(gtk.RESPONSE_OK, False)


    def on_domain_combo_changed(self, *args):
        """
        Change the search domain.  Resets the expression table and
        deletes all the expression rows.
        """
        if self._first_choice:
            self.domain_combo.remove_text(0)
            self._first_choice = False

        for kid in self.expressions_table.get_children():
            self.expressions_table.remove(kid)
        self.expressions_table.props.n_rows = 1
        del self.expression_rows[:]
        self.add_button.props.sensitive = True
        self.add_expression_row()
        self.expressions_table.show_all()


    def validate(self):
        """
        Validate the search expression is a valid expression.
        """
        valid = False
        for row in self.expression_rows:
            sensitive = False
            value = None
            if isinstance(row.value_widget, gtk.Entry):
                value = row.value_widget.props.text
            elif isinstance(row.value_widget, gtk.ComboBox):
                value = row.value_widget.get_active() >= 0

            if value and row.menu_item_activated:
                valid = True
            else:
                valid = False
                break

        self.set_response_sensitive(gtk.RESPONSE_OK, valid)
        return valid



    def remove_expression_row(self, row):
        """
        Remove a row from the expressions table.
        """
        map(self.expressions_table.remove, row.get_widgets())
        self.expressions_table.props.n_rows -= 1
        self.expression_rows.remove(row)
        del row


    def add_expression_row(self):
        """
        Add a row to the expressions table.
        """
        domain = self.domain_map[self.domain_combo.get_active_text()]
        self.mapper = class_mapper(domain)
        row = ExpressionRow(self, self.remove_expression_row)
        self.set_response_sensitive(gtk.RESPONSE_OK, False)
        self.expression_rows.append(row)
        self.expressions_table.show_all()


    def start(self):
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
        self.expressions_table = gtk.Table()
        self.expressions_table.props.column_spacing = 10
        frame.add(self.expressions_table)
        self.vbox.pack_start(frame, expand=False, fill=False)

        # add button to add additional expression rows
        self.add_button = gtk.Button()
        self.add_button.props.sensitive = False
        img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
        self.add_button.props.image = img
        self.add_button.connect("clicked", lambda w: self.add_expression_row())
        align = gtk.Alignment(0, 0, 0, 0)
        align.add(self.add_button)
        self.vbox.pack_end(align, fill=False, expand=False)

        self.vbox.show_all()
        response = self.run()
        self.hide()
        return response


    def get_query(self):
        """
        Return query expression string.
        """

        domain = self.domain_combo.get_active_text()
        query = [domain, 'where']
        for row in self.expression_rows:
            expr = row.get_expression()
            if expr:
                query.append(expr)
        return ' '.join(query)



if __name__ == '__main__':
    import bauble.test
    uri = 'sqlite:///:memory:'
    bauble.test.init_bauble(uri)
    qb = QueryBuilder()
    qb.start()
    debug(qb.get_query())

