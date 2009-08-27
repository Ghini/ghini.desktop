#
# view.py
#
# Description: the default view
#
import sys
import re
import traceback
import itertools

import gtk
import gobject
import pango
from sqlalchemy import *
from sqlalchemy.orm import *
import sqlalchemy.sql
import sqlalchemy.exc as saexc
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.properties import ColumnProperty, PropertyLoader

import bauble
import bauble.db as db
from bauble.error import check, CheckConditionError, BaubleError
import bauble.pluginmgr as pluginmgr
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.utils.log import debug, error, warning
from bauble.utils.pyparsing import *

# use different formatting template for the result view depending on the
# platform
_mainstr_tmpl = '<b>%s</b>'
if sys.platform == 'win32':
    _substr_tmpl = '%s'
else:
    _substr_tmpl = '<small>%s</small>'


class Action(gtk.Action):

    """
    An Action allows a label, tooltip, callback and accelerator to be called
    when specific items are selected in the SearchView
    """
    # TODO: multiselect and singleselect are really specific to the
    # SearchView and we could probably generalize this class a little
    # bit more...or we just assume this class is specific to the
    # SearchView and document it that way

    def __init__(self, name, label, tooltip=None, stock_id=None,
                 callback=None, accelerator=None,
                 multiselect=False, singleselect=True):
        """
        callback: the function to call when the the action is activated
        accelerator: accelerator to call this action
        multiselect: show menu when multiple items are selected
        singleselect: show menu when single items are selected

        The activate signal is not automatically connected to the
        callback method.
        """
        super(Action, self).__init__(name, label, tooltip, stock_id)
        self.callback = callback
        self.multiselect = multiselect
        self.singleselect = singleselect
        self.accelerator = accelerator

    def _set_enabled(self, enable):
        self.set_visible(enable)
        # if enable:
        #     self.connect_accelerator()
        # else:
        #     self.disconnect_accelerator()


    def _get_enabled(self):
        return self.get_visible()

    enabled = property(_get_enabled, _set_enabled)



class InfoExpander(gtk.Expander):
    """
    an abstract class that is really just a generic expander with a vbox
    to extend this you just have to implement the update() method
    """

    # preference for storing the expanded state
    expanded_pref = None

    def __init__(self, label, widgets=None):
        """
        :param label: the name of this info expander, this is displayed on the
        expander's expander
        :param glade_xml: a gtk.glade.XML instace where can find the expanders
        widgets
        """
        super(InfoExpander, self).__init__(label)
        self.vbox = gtk.VBox(False)
        self.vbox.set_border_width(5)
        self.add(self.vbox)
        self.widgets = widgets
        if not self.expanded_pref:
            self.set_expanded(True)
        self.connect("notify::expanded", self.on_expanded)


    def on_expanded(self, expander, *args):
        if self.expanded_pref:
            prefs[self.expanded_pref] = expander.get_expanded()
            prefs.save()


    def set_widget_value(self, widget_name, value, markup=True, default=None):
        '''
        a shorthand for L{bauble.utils.set_widget_value()}
        '''
        utils.set_widget_value(self.widgets[widget_name], value,
                               markup, default)


    def update(self, value):
        '''
        This method should be implemented by classes that extend InfoExpander
        '''
        raise NotImplementedError("InfoExpander.update(): not implemented")



class PropertiesExpander(InfoExpander):

    def __init__(self):
        super(PropertiesExpander, self).__init__(_('Properties'))
        table = gtk.Table(rows=4, columns=2)
        table.set_col_spacings(15)
        table.set_row_spacings(8)

        # database id
        id_label = gtk.Label(_("<b>ID:</b>"))
        id_label.set_use_markup(True)
        id_label.set_alignment(1, .5)
        self.id_data = gtk.Label('--')
        self.id_data.set_alignment(0, .5)
        table.attach(id_label, 0, 1, 0, 1)
        table.attach(self.id_data, 1, 2, 0, 1)

        # object type
        type_label = gtk.Label(_("<b>Type:</b>"))
        type_label.set_use_markup(True)
        type_label.set_alignment(1, .5)
        self.type_data = gtk.Label('--')
        self.type_data.set_alignment(0, .5)
        table.attach(type_label, 0, 1, 1, 2)
        table.attach(self.type_data, 1, 2, 1, 2)

        # date created
        created_label = gtk.Label(_("<b>Date created:</b>"))
        created_label.set_use_markup(True)
        created_label.set_alignment(1, .5)
        self.created_data = gtk.Label('--')
        self.created_data.set_alignment(0, .5)
        table.attach(created_label, 0, 1, 2, 3)
        table.attach(self.created_data, 1, 2, 2, 3)

        # date last updated
        updated_label = gtk.Label(_("<b>Last updated:</b>"))
        updated_label.set_use_markup(True)
        updated_label.set_alignment(1, .5)
        self.updated_data = gtk.Label('--')
        self.updated_data.set_alignment(0, .5)
        table.attach(updated_label, 0, 1, 3, 4)
        table.attach(self.updated_data, 1, 2, 3, 4)

        box = gtk.HBox()
        box.pack_start(table, expand=False, fill=False)
        self.vbox.pack_start(box, expand=False, fill=False)


    def update(self, row):
        """"
        Update the widget in the expander.
        """
        self.id_data.set_text(str(row.id))
        self.type_data.set_text(str(type(row).__name__))
        self.created_data.set_text(str(row._created))
        self.updated_data.set_text(str(row._last_updated))



class InfoBoxPage(gtk.ScrolledWindow):
    """
    A :class:`gtk.ScrolledWindow` that contains
    :class:`bauble.view.InfoExpander` objects.
    """

    def __init__(self):
        super(InfoBoxPage, self).__init__()
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(10)
        viewport = gtk.Viewport()
        viewport.add(self.vbox)
        self.add(viewport)
        self.expanders = {}
        self.label = None


    def add_expander(self, expander):
        '''
        Add an expander to the list of exanders in this infobox

        :param expander: the bauble.view.InfoExpander to add to this infobox
        '''
        self.vbox.pack_start(expander, expand=False, fill=True, padding=5)
        self.expanders[expander.get_property("label")] = expander

        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)


    def get_expander(self, label):
        """
        Returns an expander by the expander's label name

        :param label: the name of the expander to return
        """
        if label in self.expanders:
            return self.expanders[label]
        else: return None


    def remove_expander(self, label):
        """
        Remove expander from the infobox by the expander's label bel

        :param label: the name of th expander to remove

        Return the expander that was removed from the infobox.
        """
        if label in self.expanders:
            return self.vbox.remove(self.expanders[label])


    def update(self, row):
        """
        Updates the infobox with values from row

        :param row: the mapper instance to use to update this infobox,
          this is passed to each of the infoexpanders in turn
        """
        for expander in self.expanders.values():
            expanders.update(row)



class InfoBox(gtk.Notebook):
    """
    Holds list of expanders with an optional tabbed layout.

    The default is to not use tabs. To create the InfoBox with tabs
    use InfoBox(tabbed=True).  When using tabs then you can either add
    expanders directly to the InfoBoxPage or using
    InfoBox.add_expander with the page_num argument.
    """

    def __init__(self, tabbed=False):
        super(InfoBox, self).__init__()
        self.row = None
        self.set_property('show-border', False)
        if not tabbed:
            page = InfoBoxPage()
            self.insert_page(page, position=0)
            self.set_property('show-tabs', False)
        self.set_current_page(0)
        self.connect('switch-page', self.on_switch_page)


    # TODO: this seems broken: self == notbook
    def on_switch_page(self, notebook, dummy_page, page_num,  *args):
        """
        Called when a page is switched
        """
        if not self.row:
            return
        page = self.get_nth_page(page_num)
        page.update(self.row)


    def add_expander(self, expander, page_num=0):
        """
        Add an expander to a page.

        :param expander: The expander to add.
        :param page_num: The page number in the InfoBox to add the expander.
        """
        page = self.get_nth_page(page_num)
        page.add_expander(expander)


    def update(self, row):
        """
        Update the current page with row.
        """
        self.row = row
        page_num = self.get_current_page()
        self.get_nth_page(page_num).update(row)



# TODO: should be able to just to a add_link(uri, description) to
# add buttons
## class LinkExpander(InfoExpander):

##     def __init__(self):
##         super(LinkExpander, self).__init__()

##     def add_button(button):
##         self.vbox.pack_start(button)


class SearchParser(object):
    """
    The parser for bauble.view.MapperSearch
    """
    value_chars = Word(alphanums + '%.-_*')
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
    _properties = {}

    def __init__(self):
        super(MapperSearch, self).__init__()
        self._results = ResultSet()
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
            for d in domain:
                self._domains[d] = cls, properties
        else:
            self._domains[d] = cls, properties
        self._properties[cls] = properties


    def on_query(self, s, loc, tokens):
        """
        Called when the parser hits a query token.

        Queries can use more database specific features.  This also
        means that the same query might not work the same on different
        database types. For example, on a PostgreSQL database you can
        use ilike but this would raise an error on SQLite.
        """
        # We build the queries by fetching the ids of the rows that
        # match the condition and then returning a query to return the
        # object that have ids in the built query.  This might seem
        # like a roundabout way but it works on databases don't
        # support union and/or intersect
        #
        # TODO: support 'not' as well, e.g sp where
        # genus.genus=Maxillaria and not genus.family=Orchidaceae
        domain, expr = tokens
        check(domain in self._domains, 'Unknown search domain: %s' % domain)
        cls = self._domains[domain][0]
        mapper = class_mapper(cls)
        expr_iter = iter(expr)
        op = None
        id_query = self._session.query(cls.id)
        clause = prev_clause = None
        for e in expr_iter:
            idents, cond, val = e
            #debug('idents: %s, cond: %s, val: %s' % (idents, cond, val))

            if val == 'None':
                val = None

            if len(idents) == 1:
                # we get here when the idents only refer to a property
                # on the mapper table
                col = idents[0]
                check(col in mapper.c, 'The %s table does not have a '\
                       'column named %s' % \
                       (mapper.local_table.name, col))
                q = id_query.filter(getattr(cls, col).\
                                        op(cond)(utils.utf8(val)))
                clause = cls.id.in_(q.statement)
            else:
                # we get here when the idents refer to a relation on a
                # mapper/table
                relations = idents[:-1]
                col = idents[-1]
                # TODO: do all the databases quote the same?
                if val is None and cond in ('=', '==', 'is'):
                    cond = 'is'
                    val = 'NULL'
                elif val is None and cond in ('!='):
                    cond = 'is not'
                    val = 'NULL'
                elif val is not None:
                    # use is not None b/c val could be ''
                    val = "'%s'" % val

                if col in cls.__table__.c and \
                        relations[-1] == cls.__table__.name:
                    where = "%s %s %s" % ('.'.join(idents), cond, val)
                elif len(relations) and relations[-1] in \
                        [t.name for t in bauble.db.metadata.sorted_tables]:
                    # We get here when there are identifiers before
                    # the column and the next to the last ident is a
                    # table. Usually this means that the next to the
                    # last ident is a table and not a join.  This
                    # allows us to be more specific about the col in
                    # the case that it is ambiguous.
                    where = "%s.%s %s %s" % (idents[-2], col, cond, val)
                else:
                    where = "%s %s %s" % (col, cond, val)

                clause = cls.id.in_(id_query.join(*relations).\
                                    filter(where).statement)

            if op is not None:
                check(op in ('and', 'or'), 'Unsupported operator: %s' % op)
                op = getattr(sqlalchemy.sql, '%s_' % op)
                clause = op(prev_clause, clause)
            prev_clause = clause
            try:
                op = expr_iter.next()
            except StopIteration:
                pass

        from bauble.plugins.plants.species import Species
        if isinstance(cls, Species):
            self._results.add(self._session.query(cls).filter(clause).\
                                  options.eagerload("genus.family"))
        else:
            self._results.add(self._session.query(cls).filter(clause))



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
            cls, properties = self._domains[domain]
        except KeyError:
            raise KeyError(_('Unknown search domain: %s' % domain))

	query = self._session.query(cls)

	# select all objects from the domain
        if values == '*':
            self._results.add(query)
            return

        # TODO: should probably create a normalize_cond() method
        # to convert things like contains and has into like conditions

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
            # TODO: i don't know how well this will work out if we're
            # search for numbers
            ors = or_(*map(condition(col), values))
            self._results.add(query.filter(ors))
        return tokens


    def on_value_list(self, s, loc, tokens):
        """
        Called when the parser hits a value_list token

        Search with a list of values is the broadest search and
        searches all the mapper and the properties configured with
        add_meta()
        """
        #debug('values: %s' % tokens)
#         debug('  s: %s' % s)
#         debug('  loc: %s' % loc)
#         debug('  toks: %s' % tokens)
        # TODO: should also combine all the values into a single
        # string and search for that string

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
            self._results.add(q)


    def search(self, text, session):
        """
        Returns a ResultSet of database hits for the text search string.

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
        return self._results



# TODO: it would handy if we could support some sort of smart slicing
# where we chould slice across the different sets and still return the
# query values using LIMIT queries
class ResultSet(object):
    '''
    A ResultSet represents a set of results returned from a query, it
    allows you to add results to the set and then iterate over all the
    results as if they were one set.  It will only return objects that
    are unique between all the results.
    '''
    def __init__(self, results=None):
	self._results = set()
	if results:
	    self.add(results)


    def add(self, results):
        if isinstance(results, (list, tuple, set)):
            self._results.update(results)
        else:
            self._results.add(results)


    def __len__(self):
        # it's possible, but unlikely that int() can truncate the value
        return int(self.count())


    def count(self):
        '''
        return the number of total results from all of the members of this
        results set, does not take into account duplicate results
        '''
        ctr = 0
        for r in self._results:
            if isinstance(r, Query):
                ctr += r.count()
            elif hasattr(r, '__iter__'):
                ctr += len(r)
            else:
                ctr += 1
        return ctr


    def __iter__(self):
        # If this ResultSet contains other ResultSets that are large
        # we'll be creating lots of large set objects. This shouldn't
        # be too much of a problem since the sets would only be
        # holding references to the same object
        self._iterset = set()
        self._iter = itertools.chain(*self._results)
        return self


    def next(self):
        '''
        returns unique items from the result set
        '''
        v = self._iter.next()
        if v not in self._iterset: # only return unique objects
            self._iterset.add(v)
            return v
        else:
            return self.next()


    def clear(self):
        """
        Clear out the set.
        """
        del self._results
        self._results = set()



class SearchView(pluginmgr.View):
    """
    The SearchView is the main view for Bauble.  It manages the search
    results returned when search strings are entered into the main
    text entry.
    """

    class ViewMeta(dict):
        """
        This class shouldn't need to be instantiated directly.  Access
        the meta for the SearchView with the
        :class:`bauble.view.SearchView`'s view_meta property.
        """
        class Meta(object):
            def __init__(self):
                self.children = None
                self.infobox = None
                self.markup_func = None
                self.actions = []


            def set(self, children=None, infobox=None, context_menu=None,
                    markup_func=None):
                '''
                :param children: where to find the children for this type,
                    can be a callable of the form C{children(row)}

                :param infobox: the infobox for this type

                :param context_menu: a dict describing the context menu used
                when the user right clicks on this type

                :param markup_func: the function to call to markup
                search results of this type, if markup_func is None
                the instances __str__() function is called...the
                strings returned by this function should escape any
                non markup characters
                '''
                self.children = children
                self.infobox = infobox
                self.markup_func = markup_func
                self.context_menu = context_menu
                self.actions = []
                if self.context_menu:
                    self.actions = filter(lambda x: isinstance(x, Action),
                                          self.context_menu)


            def get_children(self, obj):
                '''
                :param obj: get the children from obj according to
                self.children, the returned object should support __len__,
                if you want to return a query then wrap it in a ResultSet
                '''
                if self.children is None:
                    return []
                if callable(self.children):
                    return self.children(obj)
                return getattr(obj, self.children)


        def __getitem__(self, item):
            if item not in self: # create on demand
                self[item] = self.Meta()
            return self.get(item)

    view_meta = ViewMeta()


    '''
    the search strategy is keyed by domain and each value will be a list of
    SearchStrategy instances
    '''
    search_strategies = [MapperSearch()]

    @classmethod
    def add_search_strategy(cls, strategy):
        cls.search_strategies.append(strategy())


    @classmethod
    def get_search_strategy(cls, name):
        for strategy in cls.search_strategies:
            if strategy.__class__.__name__ == name:
                return strategy


    def __init__(self):
        '''
        the constructor
        '''
        super(SearchView, self).__init__()
        self.create_gui()

        # we only need this for the timeout version of populate_results
        self.populate_callback_id = None

        # the context menu cache holds the context menus by type in the results
        # view so that we don't have to rebuild them every time
        self.context_menu_cache = {}
        self.infobox_cache = {}
        self.infobox = None

        # keep all the search results in the same session, this should
        # be cleared when we do a new search
        self.session = bauble.Session()


    def update_infobox(self):
        '''
        sets the infobox according to the currently selected row
        or remove the infobox is nothing is selected
        '''
        self.set_infobox_from_row(None)
        values = self.get_selected_values()
        if len(values) == 0:
            return
        try:
            self.set_infobox_from_row(values[0])
        except Exception, e:
            debug('SearchView.update_infobox: %s' % e)
            debug(traceback.format_exc())
            debug(values)
            self.set_infobox_from_row(None)


    def set_infobox_from_row(self, row):
        '''
        get the infobox from the view meta for the type of row and
        set the infobox values from row

        :param row: the row to use to update the infobox
        '''
        # remove the current infobox if there is one and stop
#        debug('set_infobox_from_row: %s --  %s' % (row, repr(row)))
        if row is None:
            if self.infobox is not None and self.infobox.parent == self.pane:
                self.pane.remove(self.infobox)
            return

        new_infobox = None
        selected_type = type(row)

        # check if we've already created an infobox of this type,
        # if not create one and put it in self.infobox_cache
        if selected_type in self.infobox_cache.keys():
            new_infobox = self.infobox_cache[selected_type]
        elif selected_type in self.view_meta and \
          self.view_meta[selected_type].infobox is not None:
            new_infobox = self.view_meta[selected_type].infobox()
            self.infobox_cache[selected_type] = new_infobox

        # remove any old infoboxes connected to the pane
        if self.infobox is not None and \
          type(self.infobox) != type(new_infobox):
            if self.infobox.parent == self.pane:
                self.pane.remove(self.infobox)

        # update the infobox and put it in the pane
        self.infobox = new_infobox
        if self.infobox is not None:
            self.pane.pack2(self.infobox, resize=False, shrink=True)
            self.pane.show_all()
            self.infobox.update(row)


    def get_selected_values(self):
        '''
        Return the values in all the selected rows.
        '''
        model, rows = self.results_view.get_selection().get_selected_rows()
        if model is None:
            return None
        return [model[row][0] for row in rows]


    def on_cursor_changed(self, view):
        '''
        Update the infobox and switch the accelerators depending on the
        type of the row that the cursor points to.
        '''
        self.update_infobox()

        # switch the accelerators depending on what the cursor is
        # currently pointing to
        for accel, cb in self.installed_accels:
            # disconnect previously installed accelerators by
            # the key and modifier,
            # accel_group.disconnect_by_func won't work here
            # since we install a closure as the actual
            # callback in instead of the original
            # action.callback
            r = self.accel_group.disconnect_key(accel[0], accel[1])
            if not r:
                warning('callback not removed: %s' % cb)
        self.installed_accels = []

        selected = self.get_selected_values()
        if not selected:
            return
        selected_type = type(selected[0])

        for action in self.view_meta[selected_type].actions:
            enabled = (len(selected) > 1 and action.multiselect) or \
                (len(selected)<=1 and action.singleselect)
            if not enabled:
                continue
            # if enabled the connect then accelerator
            keyval, mod = gtk.accelerator_parse(action.accelerator)
            if (keyval, mod) != (0, 0):
                def cb(func):
                    return lambda *args: func(selected)
                self.accel_group.connect_group(keyval, mod,
                                               gtk.ACCEL_VISIBLE,
                                               cb(action.callback))
                self.installed_accels.append(((keyval, mod), action.callback))


    nresults_statusbar_context = 'searchview.nresults'


    def search(self, text):
        '''
        search the database using text
        '''
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from
        # outside the class so the entry and search results match
#        debug('SearchView.search(%s)' % text)
        results = ResultSet()
        error_msg = None
        error_details_msg = None
        self.session.close()
        # create a new session for each search...maybe we shouldn't
        # even have session as a class attribute
        self.session = bauble.Session()
        bold = '<b>%s</b>'
        try:
            for strategy in self.search_strategies:
                results.add(strategy.search(text, self.session))
        except ParseException, err:
            error_msg = _('Error in search string at column %s') % err.column
        except (BaubleError, AttributeError, Exception, SyntaxError), e:
            #debug(traceback.format_exc())
            error_msg = _('** Error: %s') % utils.xml_safe_utf8(e)
            error_details_msg = utils.xml_safe_utf8(traceback.format_exc())

        if error_msg:
            bauble.gui.show_error_box(error_msg, error_details_msg)
            return

        # not error
        utils.clear_model(self.results_view)
        self.set_infobox_from_row(None)
        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        statusbar.pop(sbcontext_id)
        if len(results) == 0:
            model = gtk.ListStore(str)
            model.append([bold % _('Couldn\'t find anything')])
            self.results_view.set_model(model)
        else:
            if len(results) > 5000:
                msg = _('This query returned %s results.  It may take a '\
                        'long time to get all the data. Are you sure you '\
                        'want to continue?') % len(results)
                if not utils.yes_no_dialog(msg):
                    return
            statusbar.push(sbcontext_id, _("Retrieving %s search " \
                                           "results...") % len(results))
            try:
                # don't bother with a task if the results are small,
                # this keeps the screen from flickering when the main
                # window is set to a busy state
                #import time
                #start = time.time()
                if len(results) > 1000:
                    self.populate_results(results)
                else:
                    task = self._populate_worker(results)
                    while True:
                        try:
                            task.next()
                        except StopIteration:
                            break
                #debug(time.time() - start)
            except StopIteration:
                return
            else:
                statusbar.pop(sbcontext_id)
                statusbar.push(sbcontext_id,
                               _("%s search results") % len(results))
                self.results_view.set_cursor(0)


    def remove_children(self, model, parent):
        """
        remove all children of some parent in the model, reverse
        iterate through them so you don't invalidate the iter
        """
        while model.iter_has_child(parent):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids-1)
            model.remove(child)


    def on_test_expand_row(self, view, treeiter, path, data=None):
        '''
        look up the table type of the selected row and if it has
        any children then add them to the row
        '''
        expand = False
        model = view.get_model()
        row = model.get_value(treeiter, 0)
        view.collapse_row(path)
        self.remove_children(model, treeiter)
        try:
            kids = self.view_meta[type(row)].get_children(row)
            if len(kids) == 0:
                return True
        except saexc.InvalidRequestError, e:
            #debug(utils.utf8(e))
            model = self.results_view.get_model()
            for found in utils.search_tree_model(model, row):
                model.remove(found)
            return True
        except Exception, e:
            debug(utils.utf8(e))
            debug(traceback.format_exc())
            return True
        else:
            self.append_children(model, treeiter, kids)
            return False


    def populate_results(self, results, check_for_kids=False):
        """
        :param results: a ResultSet instance
        :param check_for_kids: only used for testing

        This method adds results to the search view in a task.
        """
        bauble.task.queue(self._populate_worker(results, check_for_kids))


    def _populate_worker(self, results, check_for_kids=False):
        """
        Generator function for adding the search results to the
        model. This method is usually called by self.populate_results()
        """
        nresults = len(results)
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1)
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        utils.clear_model(self.results_view)

        # group the results by type. this is where all the results are
        # actually fetched from the database
        groups = []
        for key, group in itertools.groupby(results, lambda x: type(x)):
            groups.append(list(group))
            # sorting the results here is dead slow
            #groups.append(sorted(group, key=utils.natsort_key))

        # sort the groups by type so we more or less always get the
        # results by type in the same order
        groups = sorted(groups, key=lambda x: type(x[0]))

        chunk_size = 100
        update_every = 200
        steps_so_far = 0

        # iterate over slice of size "steps", yield after adding each
        # slice to the model
        #for obj in itertools.islice(itertools.chain(*groups), 0,None, steps):
        #for obj in itertools.islice(itertools.chain(results), 0,None, steps):
        for obj in itertools.chain(*groups):
            parent = model.append(None, [obj])
            obj_type = type(obj)
            if check_for_kids:
                kids = self.view_meta[obj_type].get_children(obj)
                if len(kids) > 0:
                    model.append(parent, ['-'])
            elif self.view_meta[obj_type].children is not None:
                model.append(parent, ['-'])

            #steps_so_far += chunk_size
            steps_so_far += 1
            if steps_so_far % update_every == 0:
                percent = float(steps_so_far)/float(nresults)
                if 0< percent < 1.0:
                    bauble.gui.progressbar.set_fraction(percent)
                yield
        self.results_view.freeze_child_notify()
        self.results_view.set_model(model)
        self.results_view.thaw_child_notify()


    def append_children(self, model, parent, kids):
        """
        append object to a parent iter in the model

        :param model: the model the append to
        :param parent:  the parent gtk.TreeIter
        :param kids: a list of kids to append
        @return: the model with the kids appended
        """
        check(parent is not None, "append_children(): need a parent")
        for k in kids:
            i = model.append(parent, [k])
            if self.view_meta[type(k)].children is not None:
                model.append(i, ["_dummy"])
        return model


    def cell_data_func(self, col, cell, model, treeiter):
        value = model[treeiter][0]

        # TODO: maybe we should cache the strings on our side and then
        # detect if the objects have been changed in their session in
        # order to determine if the cache should be invalidated

        #debug('%s(%s)' % (value, type(value)))
        path = model.get_path(treeiter)
        tree_rect = self.results_view.get_visible_rect()
        cell_rect = self.results_view.get_cell_area(path, col)
        if cell_rect.y > tree_rect.height:
            # only update the cells if they're visible...this
            # drastically speeds up populating the view with large
            # datasets
            return

        if isinstance(value, basestring):
            cell.set_property('markup', value)
        else:
            try:
                func = self.view_meta[type(value)].markup_func
                if func is not None:
                    r = func(value)
                    if isinstance(r, (list,tuple)):
                        main, substr = r
                    else:
                        main = r
                        substr = '(%s)' % type(value).__name__
                else:
                    main = utils.xml_safe(str(value))
                    substr = '(%s)' % type(value).__name__
                cell.set_property('markup', '%s\n%s' % \
                                  (_mainstr_tmpl % utils.utf8(main),
                                   _substr_tmpl % utils.utf8(substr)))

            except (saexc.InvalidRequestError, TypeError), e:
                warning('bauble.view.SearchView.cell_data_func(): \n%s' % e)
                def remove():
                    model = self.results_view.get_model()
                    self.results_view.set_model(None) # detach model
                    for found in utils.search_tree_model(model, value):
                        model.remove(found)
                    self.results_view.set_model(model)
                gobject.idle_add(remove)


    def get_expanded_rows(self):
        '''
        return all the rows in the model that are expanded
        '''
        expanded_rows = []
        expand = lambda view, path: \
            expanded_rows.append(gtk.TreeRowReference(view.get_model(), path))
        self.results_view.map_expanded_rows(expand)
        # seems to work better if we passed the reversed rows to
        # self.expand_to_all_refs
        expanded_rows.reverse()
        return expanded_rows


    def expand_to_all_refs(self, references):
        '''
        :param references: a list of TreeRowReferences to expand to

        Note: This method calls get_path() on each
        gtk.TreeRowReference in <references> which apparently
        invalidates the reference.
        '''
        for ref in references:
            if ref.valid():
                self.results_view.expand_to_path(ref.get_path())


    def on_view_button_release(self, view, event, data=None):
        """
        Popup a context menu on the selected row.
        """
        # TODO: should probably fix this so you can right click on something
        # that is not the selection, but get the path from where the click
        # happened, make that that selection and then popup the menu,
        # see the pygtk FAQ about this at
        #http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq13.017.htp
        if event.button != 3:
            return False # if not right click then leave

        selected = self.get_selected_values()
        if not selected:
            return
        selected_type = type(selected[0])
        if len(selected) > 1:
            # make sure all the selected items are of the same type
            istype = set(map(lambda o: isinstance(o, selected_type), selected))
            # TODO: only show menu if all the types are the same, else
            # show the common menu
            if False in istype:
                #debug('not all the same type')
                raise NotImplementedError('calling an action on multiple '\
                                              'types is not yet supported')
                return False
            else:
                #debug('ALL the same type')
                pass

        if not self.view_meta[selected_type].actions:
            # no actions
            return True

        # TODO: ** important ** we need a common menu for all types
        # that can be merged with the specific menu for the selection,
        # e.g. provide a menu with a "Tag" action so you can tag
        # everything...or we could just ignore this and add "Tag" to
        # all of our action lists
        menu = None
        try:
            menu = self.context_menu_cache[selected_type]
        except KeyError:
            menu = gtk.Menu()
            for action in self.view_meta[selected_type].actions:
                #debug('path: %s' %  action.get_accel_path())
                item = action.create_menu_item()
                def on_activate(item, cb):
                    result = False
                    try:
                        # have to get the selected values again here
                        # because for some unknown reason using the
                        # "selected" variable from the parent scope
                        # will give us the objects but they won't be
                        # in an session...maybe its a thread thing
                        values = self.get_selected_values()
                        result = cb(values)
                    except Exception, e:
                        msg = utils.xml_safe_utf8(str(e))
                        tb = utils.xml_safe_utf8(traceback.format_exc())
                        utils.message_details_dialog(msg, tb,gtk.MESSAGE_ERROR)
                        warning(traceback.format_exc())
                    if result:
                        self.reset_view()
                item.connect('activate', on_activate, action.callback)
                menu.append(item)
            self.context_menu_cache[selected_type] = menu

        # enable/disable the menu items depending on the selection
        for action in self.view_meta[selected_type].actions:
            action.enabled = (len(selected) > 1 and action.multiselect) or \
                (len(selected)<=1 and action.singleselect)

        menu.popup(None, None, None, event.button, event.time)
        return True


    def reset_view(self):
        """
        Expire all the children in the model, collapse everything,
        reexpand the rows to the previous state where possible and
        update the infobox.
        """
        model, paths = self.results_view.get_selection().get_selected_rows()
        ref = gtk.TreeRowReference(model, paths[0])
        self.session.expire_all()

        # the invalidate_str_cache() method are specific to Species
        # and Accession right now....its a bit of a hack since there's
        # no real interface that the method complies to...but it does
        # fix our string caching issues
        def invalidate_cache(model, path, treeiter, data=None):
            obj = model[path][0]
            if hasattr(obj, 'invalidate_str_cache'):
                obj.invalidate_str_cache()
        model.foreach(invalidate_cache)
        expanded_rows = self.get_expanded_rows()
        self.results_view.collapse_all()
        # expand_to_all_refs will invalidate the ref so get the path first
        path = None
        if ref.valid():
            path = ref.get_path()
        self.expand_to_all_refs(expanded_rows)
        self.results_view.set_cursor(path)


    def on_view_row_activated(self, view, path, column, data=None):
        '''
        expand the row on activation
        '''
        view.expand_row(path, False)


    def create_gui(self):
        '''
        create the interface
        '''
        # create the results view and info box
        self.results_view = gtk.TreeView() # will be a select results row
        self.results_view.set_headers_visible(False)
        self.results_view.set_rules_hint(True)
        #self.results_view.set_fixed_height_mode(True)
        #self.results_view.set_fixed_height_mode(False)

        selection = self.results_view.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.results_view.set_rubber_banding(True)

        renderer = gtk.CellRendererText()
        renderer.set_fixed_height_from_font(2)
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn("Name", renderer)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_cell_data_func(renderer, self.cell_data_func)
        self.results_view.append_column(column)

        # view signals
        self.results_view.connect("cursor-changed", self.on_cursor_changed)
        self.results_view.connect("test-expand-row",
                                  self.on_test_expand_row)
        self.results_view.connect("button-release-event",
                                  self.on_view_button_release)
        def on_press(view, event):
            """
            This makes sure that we don't remove the multiple selection
            when clicking a mouse button.
            """
            if event.button == 3:
                return True
            else:
                return False
        self.results_view.connect("button-press-event", on_press)

        self.results_view.connect("row-activated",
                                  self.on_view_row_activated)


        # this group doesn't need to be added to the main window with
        # gtk.Window.add_accel_group since the group will be added
        # automatically when the view is set
        self.accel_group = gtk.AccelGroup()
        self.installed_accels = []

        # scrolled window for the results view
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.results_view)

        # pane to split the results view and the infobox, the infobox
        # is created when a row in the results is selected
        self.pane = gtk.HPaned()
        self.pane.pack1(sw, resize=True, shrink=True)
        self.pack_start(self.pane)
        self.show_all()



class HistoryView(pluginmgr.View):
    """Show the tables row in the order they were last updated
    """
    def __init__(self):
        super(HistoryView, self).__init__()
        init_gui()


    def init_gui(self):
        self.treeview = gtk.TreeView()
        column = gtk.TreeViewColumn()
        self.pack_start(self.treeview)

    def populate_history(self):
        """
        Add the history items to the view.
        """
        utils.clear_model(self.treeview)
        # TODO: this is gonna be a little problematic because the
        # markup functions and infoboxes are registered as part of the
        # SearchView so it's not obvious how we're gonna use them
        # here...i was envisioning that we would just show a list of
        # the objects by their last modified date like the searchview
        # with infoboxes and everything but maybe it would be better
        # just to show the raw columns...what might make sense would
        # be to make :history a special type of search that groups the
        # results by their dates
        model = gtk.ListStore(object, str)

class HistoryCommandHandler(pluginmgr.CommandHandler):

    def __init__(self):
        super(HistoryCommandHandler, self).__init__()
        self.view = None

    command = 'history'

    def get_view(self):
        debug("HistoryCommandHandler.get_view()")
        if not self.view:
            self.view = HistoryView()
        return self.view


    def __call__(self, arg):
        debug("HistoryCommandHandler.__call__(%s)" % arg)
        self.view.populate_history(arg)
        #self.view.search(arg)


pluginmgr.register_command(HistoryCommandHandler)


def select_in_search_results(obj):
    """
    :param obj: the object the select
    @returns: a gtk.TreeIter to the selected row

    Search the tree model for obj if it exists then select it if not
    then add it and select it.

    The the obj is not in the model then we add it.
    """
    check(obj != None, 'select_in_search_results: arg is None')
    view = bauble.gui.get_view()
    if not isinstance(view, SearchView):
        return None
    model = view.results_view.get_model()
    found = utils.search_tree_model(model, obj)
    row_iter = None
    if len(found) > 0:
        row_iter = found[0]
    else:
        row_iter = model.append(None, [obj])
        model.append(row_iter, ['-'])
    view.results_view.set_cursor(model.get_path(row_iter))
    return row_iter


class DefaultCommandHandler(pluginmgr.CommandHandler):

    def __init__(self):
        super(DefaultCommandHandler, self).__init__()
        self.view = None

    command = [None]

    def get_view(self):
        if self.view is None:
            self.view = SearchView()
        return self.view

    def __call__(self, arg):
        self.view.search(arg)

