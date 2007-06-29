#
# view.py
#
# Description: the default view
#
import sys, re, traceback
import itertools
import gtk, gobject, pango
from sqlalchemy import *
import sqlalchemy.exceptions as saexc
from sqlalchemy.orm.attributes import InstrumentedList
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.ext.selectresults import SelectResults, SelectResultsExt
from sqlalchemy.orm.properties import ColumnProperty, PropertyLoader
import bauble
from bauble.i18n import *
import bauble.pluginmgr as pluginmgr
import bauble.error as error
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.utils.log import debug
from bauble.utils.pyparsing import *

#
# NOTE: to add a new search domain do:
#
# 1. add table to search map with columns to search
# 2. add domain keys to domain map
# 3. if you want a result to expand on one of its children then
#    add the table and the default child to child_expand_map

# TODO: things todo when a result is selected
# - GBIF search results, probably have to look up specific institutions
# - search Lifemapper for distributions maps
# - give list of references and images and make then clickable if they are uris
# - show location of a plant in the garden map

# TODO: could push the search map into the table modules so each table can
# have its own search map then this module doesn't have to know about all the
# tables, it only has to query the tables module for the search map for all
# tables, could also do something similar to domain map and child expand
# map

# TODO: i don't really think that the sort column is that necessary
# in the SearchMeta since we have to sort all the results later, though
# if the results are partially sorted when we get them it make make them
# much faster to sort later, this would be worth looking into, we could also
# use the sort_column as the column to compare in the sorted method of
# populate_results

# TODO: provide a way to pin down the infobox so that changing the selection
# in the results_view doesn't change the values in the infobox

# TODO: search won't work on a unicode col. e.g. try 'acc where notes='test''

# TODO: on some search errors the connection gets invalidated, this
# happened to me on 'loc where site=test'
# UPDATE: this query doesn't invalidate the connection any more but apparantly
# there's a way that this happens so we should track it down

# TODO: it would be good to be able to search using the SIMILAR TO operator
# but we need to designate a way to show that value is a regular expression

# TODO: select first result in list on succesful search

# TODO: should we provide a way to change the results view from list to icon
# and provide an icon type to each type that can be returned and then you could
# double click on an icon to open the children of that type

# TODO: make the search result do their thing in a task so we can keep state
# and pulse the progressbar for large result sets

# TODO: it might make it easier to do some of the fancier searchs on properties
# using advanced property overriding, see...
# http://www.sqlalchemy.org/docs/adv_datamapping.myt#advdatamapping_properties_overriding

# TODO: it does seem like it would be better to use properties instead of
# columns names for searches, it would allow us to be more expressive and could
# probably avoid some of the trickery on deciding the top, we would just trust
# that the property returns what we need

# use different formatting template for the result view depending on the
# platform
_mainstr_tmpl = '<b>%s</b>'
if sys.platform == 'win32':
    _substr_tmpl = '%s'
else:
    _substr_tmpl = '<small>%s</small>'


import gc
gc.enable()
#gc.set_debug(gc.DEBUG_UNCOLLECTABLE|gc.DEBUG_INSTANCES|gc.DEBUG_OBJECTS)
#gc.set_debug(gc.DEBUG_LEAK)

# TODO: reset expander data on expand, the problem is that we don't keep the
# row around that was used to update the infoexpander, if we don't do this
# then we can't update unless the search view updates us, this means that
# the search view would have to register on_expanded on each info expander
# in the infobox

# what to display if the value in the database is None
DEFAULT_VALUE='--'

class InfoExpander(gtk.Expander):
    """
    an abstract class that is really just a generic expander with a vbox
    to extend this you just have to implement the update() method
    """
    # TODO: we should be able to make this alot more generic
    # and get information from sources other than table columns
    def __init__(self, label, widgets=None):
        """
        the constructor

        @param label: the name of this info expander, this is displayed on the
        expander's expander
        @param glade_xml: a gtk.glade.XML instace where can find the expanders
        widgets
        """
        super(InfoExpander, self).__init__(label)
        self.vbox = gtk.VBox(False)
        self.vbox.set_border_width(5)
        self.add(self.vbox)
        self.set_expanded(True)
        self.widgets = widgets


    def set_widget_value(self, widget_name, value, markup=True, default=None):
        '''
        a shorthand for L{utils.set_widget_value}
        TODO: how do i link the docs to reference utils.set_widget_value
        '''
        utils.set_widget_value(self.widgets.glade_xml, widget_name, value,
                               markup, default)


    def update(self, value):
        '''
        should be implement
        '''
        raise NotImplementedError("InfoExpander.update(): not implemented")


# should we have a specific expander for those that use glade
class GladeInfoExpander(gtk.Expander):
    pass


class InfoBox(gtk.ScrolledWindow):
    """
    a VBox with a bunch of InfoExpanders
    """

    def __init__(self):
        super(InfoBox, self).__init__()
        self.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.vbox = gtk.VBox()
        self.vbox.set_spacing(10)
        viewport = gtk.Viewport()
        viewport.add(self.vbox)
        self.add(viewport)

        self.expanders = {}


    def add_expander(self, expander):
        '''
        add an expander to the list of exanders in this infobox

        @type expander: InfoExpander
        @param expander: the expander to add to this infobox
        '''
        self.vbox.pack_start(expander, False, False)
        self.expanders[expander.get_property("label")] = expander

        sep = gtk.HSeparator()
        self.vbox.pack_start(sep, False, False)


    def get_expander(self, label):
        """
        returns an expander by the expander's label name

        @param label: the name of the expander to return
        @returns: returns an expander by the expander's label name
        """
        if label in self.expanders:
            return self.expanders[label]
        else: return None


    def remove_expander(self, label):
        """
        remove expander from the infobox by the expander's label bel

        @param label: the name of th expander to remove
        @return: return the expander that was removed from the infobox
        """
        if label in self.expanders:
            return self.vbox.remove(self.expanders[label])


    def update(self, row):
        """
        updates the infobox with values from row

        @param row: the mapper instance to use to update this infobox,
        this is passed to each of the infoexpanders in turn
        """
        # TODO: should we just iter over the expanders and update them all
        raise NotImplementedError


class GBIFLinkButton(gtk.LinkButton):

    def __init__(self, label=_('Search GBIF')):
        super(GBIFLinkButton, self).__init__(uri='http://www.gbif.nbet',
                                             label=label)


class LinkExpander(InfoExpander):

    def __init__(self):
        super(LinkExpander, self).__init__()

    def add_button(button):
        self.vbox.pack_start(button)


class SearchParser(object):
    """
    This class parses three distinct types of string. They can beL
        1. Value or a list of values: val1, val2, val3
        2. An expression where the domain is a search domain registered
           with the search meta: domain=something and val2=somethingelse,asdasd
        3. A query like:
           domain where col1=something and col2=somethingelse,asdasd
    """

    def __init__(self):
        quotes = Word('"\'')
        value_word = Word(alphanums + '%.')
        quotes = Word('"\'')
        value = (value_word | quotedString.setParseAction(removeQuotes))
        value_list = OneOrMore(value)

        binop = oneOf('= == != <> < <= > >= not like contains has ilike '\
                      'icontains ihas')

        domain = Word(alphas, alphanums)
        domain_expression = Group(domain + binop + value) \
                          | Group(domain + Literal('=') + Literal('*'))

        where_token = CaselessKeyword('where')
        and_token = CaselessKeyword('and')
        or_token = CaselessKeyword('or')
        identifier = Group(delimitedList(Word(alphas, alphanums+'_'), '.'))
        ident_expression = Group(identifier + binop + value)
        logop = and_token | or_token
        query_expressions = ident_expression + \
                            ZeroOrMore(logop + ident_expression)
        domain_query = domain + where_token.suppress() + \
                       Group(query_expressions)

        self.statement = (domain_query).setResultsName('query')+StringEnd() | \
                         (domain_expression + \
                          StringEnd()).setResultsName('expression') | \
                         value_list.setResultsName('values') + StringEnd()

    def parse_string(self, text):
        '''
        returns a pyparsing.ParseResults objects the represents  either a
        query, an expression or a list of values
        '''
        return self.statement.parseString(text)


class OperatorValidator(object):#formencode.FancyValidator):

    to_operator_map = {}

    def to_python(self, value, state=None):
        if value in self.to_operator_map:
            return self.to_operator_map[value]
        else:
            return value


    def from_python(self, value, state=None):
        return value


class SQLOperatorValidator(object):#OperatorValidator):

    def __init__(self, db_type, *args, **kwargs):
        super(SQLOperatorValidator, self).__init__(*args, **kwargs)
        type_map = {'postgres': self.pg_operator_map,
                    'sqlite': self.sqlite_operator_map,
                    'mysql': self.mysql_operator_map
                    }
        self.db_type = db_type
        self.to_operator_map = type_map.get(self.db_type, {})


    # TODO: using operators like this doesn't do the fuzzy matching
    # using like so when searching you would have to specify exactly what
    # you want, maybe we could do '=' and '!=' do fuzzy matching using like
    # and '==' and '<>' do exact matches, to do this we just
    # need to override _to_python to do a string sub on NOT LIKE(%%s%)
    pg_operator_map = {'==': '=',
               '!=': '<>',
               }
    sqlite_operator_map = {'=': '==',
               '!=': '<>'
               }
    mysql_operator_map = {'=': '==',
              '!=': '<>'
              }


class PythonOperatorValidator(object):#OperatorValidator):
    """
    convert accepted parse operators to python operators
    NOTE: this operator validator is only for python operators and doesn't
    do convert operators that may be specific to the database type
    """
    to_operator_map = {'=': '==',
               '<>': '!=',
               }


class SearchMeta(object):

    def __init__(self, mapper, columns):
        """
        @param mapper: a Mapper object
        @param columns: the names of the table columns that will be search
        """
        self.mapper = class_mapper(mapper)
        assert isinstance(columns, list), 'SearchMeta.__init__: '\
                                          'columns argument must be a list'
        self.columns = columns



class SearchStrategy(object):

    def search(self, tokens, session):
        '''
        '''
        pass


# value1, value2, value3: search mapping columns for value1, value2, value3, same as dom=value1,dom=value2,etc... for all domains
# dom=value: get mapping of domain and search specific columns
# domain where join.col = value search specific column on mapping or join for value
# domain where join = value: search columns of the mapping of join for value

# should create some sort of list of mapping: (col1, col1) to query: what about other operators for queries where you want the values or/and'ed together
class MapperSearch(SearchStrategy):

    def __init__(self, mapper, columns):
        """
        @param mapper: a Mapper object
        @param columns: the names of the table columns that will be search
        """
        self.mapper = class_mapper(mapper)
        assert isinstance(columns, list), 'SearchMeta.__init__: '\
                                          'columns argument must be a list'
        self.columns = columns


    def _resolve_identifiers(self, parent, identifiers):
        '''
        results the types of identifiers starting from parent where the
        first item in the identifiers list is either a property or column
        of parent
        '''
        def get_prop(parent, name):
            try:
                if isinstance(parent, Mapper):
                    prop = parent.props[name]
                else:
                    prop = getattr(parent, name).property
            except (KeyError, AttributeError):
                if isinstance(parent, Mapper):
                     parent_name = parent.local_table
                else:
                     parent_name = parent.__name__
                debug(parent)
                debug(name)
                raise ValueError('no column named %s in %s' % \
                                 (name, parent_name))
#            debug(prop)
            if isinstance(prop, ColumnProperty):
                # this way we don't have to support or screw around with
                # column properties that use more than one column
#                debug(parent.c[name])
                return parent.c[name]
            elif isinstance(prop, PropertyLoader):
#                debug(prop.argument)
                if isinstance(prop.argument, Mapper):
                    return prop.argument.class_
                else:
                    return prop.argument
            else:
                raise ValueError('unsupported property type: %s' % type(prop))

        props = []
#        debug('%s: %s' % (parent , identifiers))
        props.append(get_prop(parent, identifiers[0]))
        for i in xrange(1, len(identifiers)):
            parent = props[i-1]
            if isinstance(parent, Column):
                get_prop(parent, identifiers[i])
            else:
                props.append(get_prop(class_mapper(parent), identifiers[i]))
#        debug(props)
        return props


    def _build_select(self, session, mapping, identifiers, cond, val):
        '''
        return a sqlalchemy.ext.selectresults
        '''
        # TODO: this was written before the generative queries were in
        # SQLAlchemy, this should probably be rewritten to remove the
        # SelectResults dependency and just use the Query object

        # if the last item in identifiers is a column then create an
        # and statement doing applying cond to val,
        # else get the search meta for the last item in identifiers
        # and build the and_ statement by or'ing the columns in search
        # meta together against val
        query = session.query(mapping)
        sr = SelectResults(query)
        table = query.table
        resolved = self._resolve_identifiers(mapping, identifiers)
        last = resolved[-1]
        if isinstance(last, Column):
            if len(identifiers) > 1:
                # if it's a join then get the search meta columns
                # else just search on the column
                for i in identifiers[:-1]:
                    sr = sr.join_to(i)
                filter_col = resolved[-2].c[identifiers[-1]]
            else:
                filter_col = table.c[identifiers[-1]]
            sr = sr.select(filter_col.op(cond)(val))
        else:
            for i in identifiers:
                sr = sr.join_to(i)
            cols = self.search_metas[last.__name__].columns
            if cols > 1:
                ors = [last.c[c].op(cond)(val) for c in cols]
                filter_clause = or_(*ors)
            else:
                filter_clause = last.c[c].op(cond)(val)
            sr = sr.select(filter_clause)
#        debug('----- clause ----- \n %s' % sr._clause)
        return sr

    def _get_results_from_query(self, tokens, session):
        '''
        get results from search query in the form
        domain where ident=value...

        @return: an sqlalchemy.ext.selectresults object
        '''
#        debug('query: %s' % tokens['query'])
        domain, expr = tokens['query']
#        mapping = self.domain_map[domain]
#        search_meta = self.search_metas[mapping.class_.__name__]
        mapping = self.mapper.class_
        expr_iter = iter(expr)
        select = prev_select = None
        op = None
        query = session.query(mapping)
        for e in expr_iter:
            ident, cond, val = e
#            debug('ident: %s, cond: %s, val: %s' % (ident, cond, val))
            select = self._build_select(session, mapping, ident, cond, val)
            if op is not None:
                # TODO: i'm not sure how elegant building the queries like
                # this is when we have to 'op' then together but it seems to
                # work on most of the queries statements that i've tried
                prop = mapping.props[ident[0]]
                if isinstance(prop, ColumnProperty):
                    select = prev_select.select(and_(select._clause))
                else:
                    if prop.is_backref:
                        prop = prop.select_mapper.props[prop.backref.key]
                    # TODO: i haven't tested this for multiple columns on the
                    # remote side
                    for col in prop.remote_side:
                        ids = [s.id for s in select]
                        select = prev_select.select(mapping.local_table.c['id'].in_(*ids))
            try:
                op = expr_iter.next()
                prev_select = select
            except StopIteration:
                pass

#        debug(str(select._clause))
        return select

    def search(self, tokens, session=None):
        '''
        return the search results depending on how tokens were parsed
        '''

#        debug('MapperSearch.search()')
        if session is None:
            session = create_session()

        results = ResultSet()
        if 'values' in tokens:
            # make searches in postgres case-insensitive, i don't think other
            # databases support a case-insensitive like operator
            if bauble.db_engine.name == 'postgres':
                like = lambda table, col, val: \
                       table.c[col].op('ILIKE')('%%%s%%' % val)
            else:
                like = lambda table, col, val: \
                       table.c[col].like('%%%s%%' % val)
            mapping = self.mapper.class_
            q = session.query(mapping)
            sr = SelectResults(q)
            cv = [(c,v) for c in self.columns for v in tokens]
            sr = sr.select(or_(*[like(mapping, c, v) for c,v in cv]))
            results.append(sr)
        elif 'expression' in tokens:
#            print 'expr: %s' % tokens['expression']
            for domain, cond, val in tokens['expression']:
                #mapping = self.domain_map[domain]
#                debug(mapping.class_.__name__)
                #search_meta = self.search_metas[mapping.class_.__name__]
                print self.mapper
                mapping = self.mapper.class_
                query = session.query(mapping)
                # TODO: should probably create a normalize_cond() method
                # to convert things like contains and has into like conditions

                # TODO: i think that sqlite uses case insensitve like, there
                # is a pragma to change this so maybe we could send that
                # command first to handle case sensitive and insensitive
                # queries

                if cond in ('ilike', 'icontains') and \
                       bauble.db_engine.name != 'postgres':
                    msg = _('The <i>ilike</i> and <i>icontains</i> '\
                            'operators are only supported on PostgreSQL ' \
                            'databases. You are connected to a %s database.') \
                            % bauble.db_engine.name
                    utils.message_dialog(msg, gtk.MESSAGE_WARNING)
                    return results
                if cond in ('contains', 'icontains', 'has', 'ihas'):
                    val = '%%%s%%' % val
                    if cond in ('icontains', 'ihas'):
                        cond = 'ilike'
                    else:
                        cond = 'like'

                # select everything
                sr = SelectResults(query)
                if val == '*':
                    results.append(sr)
                else:
                    for col in self.columns:
                        results.append(query.select(mapping.c[col].op(cond)(val)))
        elif 'query' in tokens:
            results.append(self._get_results_from_query(tokens, session))

        return results



class ResultSet(object):
    '''
    a ResultSet represents a set of results returned from a query, it allows
    you to add results to the set and then iterate over all the results
    as if they were one set
    '''
    def __init__(self, results=None):
        if results is None:
            self._results = []
        else:
            self._results = results


    def append(self, results):
        self._results.append(results)


    def __len__(self):
        # it possible, but unlikely that int() can truncate the value
        return int(self.count())


    def count(self):
        '''
        return the number of total results from all of the members of this
        results set, does not take into account duplicate results
        '''
        ctr = 0
        for r in self._results:
            if isinstance(r, SelectResults):
                ctr += r.count()
            else:
                ctr += len(r)
        return ctr


    def __iter__(self):
        self._iter = itertools.chain(*self._results)
        self._set = set()
        return self


    def next(self):
        '''
        returns unique items from the result set
        '''
        v = self._iter.next()
        if v in self._set:
            return self.next()
        self._set.add(v)
        return v



class SearchView(pluginmgr.View):
    '''
    1. all search parameters are by default ANDed together unless two of the
    same class are give and then they are ORed, e.g. fam=... fam=... will
    give everything that matches either one\
    2. should follow some sort of precedence using AND, OR and parentheses
    3. if the search get too complicated we may have to define a language
    4. search specifically by family, genus, sp, infrasp(x?), author,
    garden location, country/region or origin, conservation status, edible
    5. possibly add families/family=Arecaceae, Orchidaceae, Poaceae
    '''


    # the search map is keyed by domain, this means that the same search
    # meta instance can be refered to by more than one key
    #search_map = {} # dictionary of search metas
    domain_map = {}
    search_metas = {}

    '''
    the search strategy is keyed by domain and each value will be a list of
    SearchStrategy instances
    '''
    search_strategies = {}

    class ViewMeta(dict):

        class Meta(object):
            def __init__(self):
                self.set()

            def set(self, children=None, infobox=None, context_menu=None,
                    markup_func=None):
                '''
                @param children: where to find the children for this type,
                    can be a callable of the form C{children(row)}
                @param infobox: the infobox for this type
                @param context_menu: a dict describing the context menu used
                when the user right clicks on this type
                @param markup_func: the function to call to markup search
                results of this type, if markup_func is None the instances
                __str__() function is called
                '''
                self.children = children
                self.infobox = infobox
                self.context_menu_desc = context_menu
                self.markup_func = markup_func


            def get_children(self, obj):
                '''
                @param obj: get the children from obj according to
                self.children
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


    @classmethod
    def register_search_strategy(cls, domain, strategy):
        '''
        @param domain: a domain or list of domains names to register
        the search strategy under, if the domain is None then the search
        strategy is used when there is no search domain specified
        will
        @param strategy: the search strategy to use for the domain(s)
        '''
        cls.search_strategies[domain] = strategy


    @classmethod
    def get_search_strategy(cls, domain):
        for d, strategy in cls.search_strategies.iteritems():
            if isinstance(d, (list, tuple)):
                if domain in d:
                    return strategy
            else:
                if d == domain:
                    return strategy


    def __init__(self):
        '''
        the constructor
        '''
        #views.View.__init__(self)
        super(SearchView, self).__init__()
        self.create_gui()
        self.parser = SearchParser()

        # we only need this for the timeout version of populate_results
        self.populate_callback_id = None

        # the context menu cache holds the context menus by type in the results
        # view so that we don't have to rebuild them every time
        self.context_menu_cache = {}
        self.infobox_cache = {}
        self.infobox = None

        # keep all the search results in the same session, this should
        # be cleared when we do a new search
        self.session = create_session()


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

        @param row: the row to use to update the infobox
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
            self.infobox.update(row)
            self.pane.pack2(self.infobox, False, True)
            self.pane.show_all()


    def get_selected_values(self):
        '''
        return all the selected rows
        '''
        model, rows = self.results_view.get_selection().get_selected_rows()
        if model is None:
            return None
        return [model[row][0] for row in rows]


    def on_results_view_select_row(self, view):
        '''
        add and removes the infobox which should change depending on
        the type of the row selected
        '''
        self.update_infobox()


    def _get_search_results_from_tokens(self, tokens):
        '''
        return the search results depending on how tokens was parsed
        '''
        results = ResultSet()
        if 'values' in tokens:
            debug('values')
            # make searches in postgres case-insensitive, i don't think other
            # databases support a case-insensitive like operator
            if bauble.db_engine.name == 'postgres':
                like = lambda table, col, val: \
                       table.c[col].op('ILIKE')('%%%s%%' % val)
            else:
                like = lambda table, col, val: \
                       table.c[col].like('%%%s%%' % val)
            for strategy in self.search_strategies.values():
                results.append(strategy.search(tokens, self.session))
        elif 'expression' in tokens:
#            print 'expr: %s' % tokens['expression']
            for domain, cond, val in tokens['expression']:
                strategy = self.get_search_strategy(domain)
                results.append(strategy.search(tokens, self.session))
        elif 'query' in tokens:
            domain, expr = tokens['query']
            strategy = self.get_search_strategy(domain)
            results = strategy.search(tokens, self.session)
        return results


    nresults_statusbar_context = 'searchview.nresults'

##     @staticmethod
##     def dump_garbage():
##         """
##         show us what's the garbage about
##         """

##         # force collection
##         print "\nGARBAGE:"
##         gc.collect()

##         print "\nGARBAGE OBJECTS:"
##         for x in gc.garbage:
##             s = str(x)
##             if len(s) > 80:
##                 s = s[:80]
##             print type(x),"\n  ", s


    def search(self, text):
        '''
        search the database using text
        '''
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from
        # outside the class so the entry and search results match
#        debug('SearchView.search(%s)' % text)
        self.session.clear()

        utils.clear_model(self.results_view)
        self.set_infobox_from_row(None)

        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        results = []
        error_msg = None
        self.session.clear() # clear out any old search results
        bold = '<b>%s</b>'
        try:
            tokens = self.parser.parse_string(text)
            results = self._get_search_results_from_tokens(tokens)
        except ParseException, err:
            error_msg = _('Error in search string at column %s') % err.column
        except (error.BaubleError, AttributeError, Exception, SyntaxError), e:
            debug(traceback.format_exc())
            error_msg = _('** Error: %s') % utils.xml_safe_utf8(e)
        if len(results) == 0:
            model = gtk.ListStore(str)
            if error_msg is not None:
                model.append([bold % error_msg])
            else:
                model.append([bold % 'Couldn\'t find anything'])
            statusbar.pop(sbcontext_id)
            self.results_view.set_model(model)
        else:
            def populate_callback():
                self.populate_results(results)
                statusbar.push(sbcontext_id, "%s results" % len(results))
                # select first item in list
                self.results_view.set_cursor(0)
            if len(results) > 2000:
                msg = 'This query returned %s results.  It may take a '\
                        'long time to get all the data. Are you sure you '\
                        'want to continue?' % len(results)
                if utils.yes_no_dialog(msg):
                    gobject.idle_add(populate_callback)
                else:
                    pass
            else:
                gobject.idle_add(populate_callback)


    def remove_children(self, model, parent):
        """
        remove all children of some parent in the model, reverse
        iterate through them so you don't invalidate the iter
        """
        while model.iter_has_child(parent):
            nkids = model.iter_n_children(parent)
            child = model.iter_nth_child(parent, nkids-1)
            model.remove(child)


    def on_test_expand_row(self, view, iter, path, data=None):
        '''
        look up the table type of the selected row and if it has
        any children then add them to the row
        '''
        expand = False
        model = view.get_model()
        row = model.get_value(iter, 0)
        view.collapse_row(path)
        self.remove_children(model, iter)
        try:
            kids = self.view_meta[type(row)].get_children(row)
            if len(kids) == 0:
                return True
        except saexc.InvalidRequestError, e:
#            debug(e)
            model = self.results_view.get_model()
            for found in utils.search_tree_model(model, row):
                model.remove(found)
            return True
        else:
            self.append_children(model, iter, kids)
            return False


    def populate_results(self, select, check_for_kids=False):
        '''
        populate the results view with the rows in select

        @param select: an iterable object to get the rows from
        @param check_for_kids: whether we should check if each of the rows in
            select have children and set the expand indicator as such, this can
            signicantly slow down large lists of data, if this is False then
            all appended rows will have an expand indicator and the children
            will be check on expansion
        '''
        utils.clear_model(self.results_view)
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1)
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
##        import logging
##        logger = logging.getLogger('sqlalchemy.engine')
##        logger.setLevel(logging.INFO)

        import time
##        start = time.time()
        groups = []
        # TODO: the natural sort probably isn't compatible for non ASCII
        # character strings
        for k, g in itertools.groupby(select, lambda x: type(x)):
            groups.append(sorted(g, key=utils.natsort_key))
##         debug(time.time()-start)

##         start = time.time()
        for s in itertools.chain(*groups):
                p = model.append(None, [s])
                selected_type = type(s)
                if check_for_kids:
                    kids = self.view_meta[selected_type].get_children(s)
                    if len(kids) > 0:
                        model.append(p, ['-'])
                elif self.view_meta[selected_type].children is not None:
                    model.append(p, ['-'])
        self.results_view.freeze_child_notify()
        self.results_view.set_model(model)
        self.results_view.thaw_child_notify()

##        debug(time.time()-start)
#        logger.setLevel(logging.ERROR)


    def append_children(self, model, parent, kids):
        '''
        append object to a parent iter in the model

        @param model: the model the append to
        @param parent:  the parent iter
        @param kids: a list of kids to append
        @return: the model with the kids appended
        '''
        assert parent is not None, "append_children(): need a parent"
        for k in kids:
            i = model.append(parent, [k])
            if self.view_meta[type(k)].children is not None:
                model.append(i, ["_dummy"])
        return model


    def cell_data_func(self, coll, cell, model, iter):
        value = model[iter][0]
#        table_name = value.__class__.__name__

        if isinstance(value, str):
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
                    main = str(value)
                    substr = '(%s)' % type(value).__name__
                cell.set_property('markup', '%s\n%s' % \
                                  (_mainstr_tmpl % utils.utf8(main),
                                   _substr_tmpl % utils.utf8(substr)))
            except (saexc.InvalidRequestError, TypeError), e:
                def remove():
                    treeview_model = self.results_view.get_model()
                    self.results_view.set_model(None) # detach model
                    for found in utils.search_tree_model(treeview_model,value):
                        treeview_model.remove(found)
                    self.results_view.set_model(treeview_model)
                gobject.idle_add(remove)


    def on_entry_key_press(self, widget, event, data=None):
        '''
        '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.search_button.emit("clicked")


    def get_expanded_rows(self):
        '''
        '''
        expanded_rows = []
        self.results_view.map_expanded_rows(lambda view, path: expanded_rows.append(gtk.TreeRowReference(view.get_model(), path)))
        # if we don't reverse them before returning them then looping over
        # them to reexpand them may cause paths that are 'lower' in the tree
        # have invalid paths
        expanded_rows.reverse()
        return expanded_rows


    def expand_to_all_refs(self, references):
        '''
        @param references: a list of TreeRowReferences to expand to
        '''
        for ref in references:
            if ref.valid():
                # use expand_to_path instead of expand_row b/c then the other
                # references that are 'lower' in the tree may have invalid
                # paths, which seems like the opposite of what tree row
                # reference is meant to do
                self.results_view.expand_to_path(ref.get_path())


    def on_view_button_release(self, view, event, data=None):
        '''
        popup a context menu on the selected row
        '''
        # TODO: should probably fix this so you can right click on something
        # that is not the selection, but get the path from where the click
        # happened, make that that selection and then popup the menu,
        # see the pygtk FAQ about this at
        #http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq13.017.htp
        # TODO: SLOW -- it can be really slow if the the callback method
        # changes the model(or what if it doesn't) and the view has to be
        # refreshed from a large dataset
        if event.button != 3:
            return # if not right click then leave

        values = self.get_selected_values()
        model, paths = self.results_view.get_selection().get_selected_rows()
        if len(paths) > 1:
            return
        selected_type = type(values[0])
        if self.view_meta[selected_type].context_menu_desc is None:
            # no context menu
            return

        menu = None
        try:
            menu = self.context_menu_cache[selected_type]
        except:
            menu = gtk.Menu()
            for label, func in self.view_meta[selected_type].context_menu_desc:
                if label == '--':
                    menu.add(gtk.SeparatorMenuItem())
                else:
                    def on_activate(item, f):
                        value = self.get_selected_values()[0]
                        expanded_rows = self.get_expanded_rows()
                        if f(value) is not None:
                            for obj in self.session:
                                try:
                                    self.session.expire(obj)
                                except saexc.InvalidRequestError:
#                                    debug('exception on refresh')
                                    # find the object in the tree and remove
                                    # it, this could get expensive if there
                                    # are a lot of items in the tree
                                    for found in utils.search_tree_model(model,
                                                                         obj):
#                                        debug('found %s: %s' % (found, model[found][0]))
                                        model.remove(found)
                            self.results_view.collapse_all()
                            self.expand_to_all_refs(expanded_rows)
                            self.update_infobox()
                    item = gtk.MenuItem(label)
                    item.connect('activate', on_activate, func)
                    menu.add(item)
            self.context_menu_cache[selected_type] = menu

        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)


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
        self.results_view.connect("cursor-changed",
                                  self.on_results_view_select_row)
        self.results_view.connect("test-expand-row",
                                  self.on_test_expand_row)
        self.results_view.connect("button-release-event",
                                  self.on_view_button_release)
        self.results_view.connect("row-activated",
                                  self.on_view_row_activated)
        # scrolled window for the results view
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(self.results_view)

        # pane to split the results view and the infobox, the infobox
        # is created when a row in the results is selected
        self.pane = gtk.HPaned()
        self.pane.pack1(sw, True, False)
        self.pack_start(self.pane)
        self.show_all()

    # TODO: should i or should i not delete everything that is a child
    # of the row when it is collapsed, this would save memory but
    # would cause it to be slow if rows were collapsed and need to be
    # reopend
#    def on_row_collapsed(self, view, iter, path, data=None):
#        '''
#        '''
#        pass



class DefaultCommandHandler(pluginmgr.CommandHandler):

    def __init__(self):
        super(DefaultCommandHandler, self).__init__()
        self.view = None

    command = None

    def get_view(self):
        if self.view is None:
            self.view = SearchView()
        return self.view

    def __call__(self, arg):
        self.view.search(arg)

