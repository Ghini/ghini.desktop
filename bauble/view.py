#
# view.py
#
# Description: the default view
#
import sys, re, traceback
import itertools
import gtk, gobject, pango
from sqlalchemy import *
from sqlalchemy.orm import *
import sqlalchemy.exceptions as saexc
from sqlalchemy.orm.mapper import Mapper
from sqlalchemy.orm.properties import ColumnProperty, PropertyLoader
import bauble
from bauble.i18n import *
import bauble.pluginmgr as pluginmgr
import bauble.error as error
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.utils.log import debug
from bauble.utils.pyparsing import *

# BUGS: - https://bugs.launchpad.net/bauble/+bug/147015 - Show
# relevant online data for search results
# https://bugs.launchpad.net/bauble/+bug/147016 - Ability to pin down
# infobox https://bugs.launchpad.net/bauble/+bug/147019 - Retrieve
# search results in a task
# https://bugs.launchpad.net/bauble/+bug/147020 - Use regular
# expressions in search strings

# TODO: should we provide a way to change the results view from list to icon
# and provide an icon type to each type that can be returned and then you could
# double click on an icon to open the children of that type

# use different formatting template for the result view depending on the
# platform
_mainstr_tmpl = '<b>%s</b>'
if sys.platform == 'win32':
    _substr_tmpl = '%s'
else:
    _substr_tmpl = '<small>%s</small>'

#import gc
#gc.enable()
#gc.set_debug(gc.DEBUG_UNCOLLECTABLE|gc.DEBUG_INSTANCES|gc.DEBUG_OBJECTS)
#gc.set_debug(gc.DEBUG_LEAK)

# TODO: reset expander data on expand, the problem is that we don't keep the
# row around that was used to update the infoexpander, if we don't do this
# then we can't update unless the search view updates us, this means that
# the search view would have to register on_expanded on each info expander
# in the infobox

# what to display if the value in the database is None
DEFAULT_VALUE = '--'

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
        self.vbox.pack_start(box)


    def update(self, row):
        self.id_data.set_text(str(row.id))
        self.type_data.set_text(str(type(row).__name__))
        self.created_data.set_text(str(row._created))
        self.updated_data.set_text(str(row._last_updated))



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



# TODO: should be able to just to a add_link(uri, description) to
# add buttons
## class LinkExpander(InfoExpander):

##     def __init__(self):
##         super(LinkExpander, self).__init__()

##     def add_button(button):
##         self.vbox.pack_start(button)


class SearchParser(object):
    """
    This class is used by MapperSarch to parses three distinct types of
    strings. They can be:
        1. Value or a list of values: val1, val2, val3
        2. An expression where the domain is a search domain registered
           with the search meta: domain=something and val2=somethingelse,asdasd
        3. A query like:
           domain where col1=something and col2=somethingelse,asdasd
    """

    def __init__(self):
#        quotes = Word('"\'')
        value_word = Word(alphanums + '%.-_')
        value = (value_word | quotedString.setParseAction(removeQuotes))
        value_list = Group(delimitedList(value) ^ OneOrMore(value))

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
        #ident_expression = identifier + binop + value
        logop = and_token | or_token
        query_expressions = ident_expression + \
                            ZeroOrMore(logop + ident_expression)
        #query_expressions = Group(ident_expression)
        domain_query = domain + where_token.suppress() + \
                       Group(query_expressions)

        self.statement = (domain_query).setResultsName('query') ^ \
            (domain_expression).setResultsName('expression') ^ \
            value_list.setResultsName('values')


    def parse_string(self, text):
        '''
        returns a pyparsing.ParseResults objects the represents  either a
        query, an expression or a list of values
        '''
        return self.statement.parseString(text)



class SearchStrategy(object):

    def search(self, text, session=None):
        '''
        @param text: the search string
        @param: the session to use for the search

        Return an interable of a list of object retrieved from the
        text search string
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
    _mapping_columns = {}

    def __init__(self):
        super(MapperSearch, self).__init__()
        self.parser = SearchParser()


    def add_meta(self, domain, mapping, default_columns):
        """
        Adds search meta to the domain
        @param domain: a string, list or tuple of domains that will resolve
        to mapping in a search string
        @param mapping: the mapping the domain will resolve to, should be a
        class that inherits from bauble.BaubleMapper
        @param default_columns: the columns to search on the mapping
        """
        assert isinstance(default_columns, list), _('MapperSearch.add_meta():'\
                ' default_columns argument must be list')
        assert len(default_columns) > 0, _('MapperSearch.add_meta(): '\
                                    'default_columns argument cannot be empty')
        if isinstance(domain, (list, tuple)):
            for d in domain:
                self._domains[d] = mapping, default_columns
        else:
            self._domains[d] = mapping, default_columns
        self._mapping_columns[mapping] = default_columns


    # TODO: _resolve_identifiers needs a test
    # TODO: we should be able to rewrite this recursively
    def _resolve_identifiers(self, parent, identifiers):
        '''
        results the types of identifiers starting from parent where the
        first item in the identifiers list is either a property or column
        of parent
        '''
        def get_prop(parent, name):
            """
            resolves the property with name on parent depending on the
            type of parent
            """
            try:
                if isinstance(parent, Mapper):
                    prop = parent.get_property(name)
                else:
                    prop = getattr(parent, name).property
            except (KeyError, AttributeError):
                if isinstance(parent, Mapper):
                    parent_name = parent.local_table
                else:
                    parent_name = parent.key
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


    def _get_results_from_query(self, tokens, session):
        """
        @param tokens: the tokens from the parsed search string,
        should match a query search expression
        @param session: the session to use to retreive the results

        Returns a sqlalchemy.orm.Query that will retreive the search
        results for the search tokens
        """
        domain, expr = tokens['query']
        assert domain in self._domains, 'Unknown search domain: %s' % domain
        mapping = self._domains[domain][0]
        expr_iter = iter(expr)
        op = None
        query = session.query(mapping)
        clause = prev_clause = None
        for e in expr_iter:
            idents, cond, val = e
##            debug('idents: %s, cond: %s, val: %s' % (idents, cond, val))
            if len(idents) == 1:
                col = idents[0]
                # TODO: at the moment this only works if the
                # identifier is a column but in theory if we should be
                # able to resolve the identifier if its not a column
                # and treat it like a search expression, maybe we
                # could create a custom search string and pass it to
                # self.search() or an sql statement from it
                assert col in mapping.c, 'The %s table does not have a '\
                       'column named %s' % \
                       (class_mapper(mapping).local_table.name, col)
                clause = mapping.c[idents[0]].op(cond)(unicode(val))
            else:
                resolved = self._resolve_identifiers(mapping, idents)
                query = query.join(idents[:-1])
                clause = resolved[-1].op(cond)(unicode(val))

            if op is not None:
                assert op in ('and', 'or'), 'Unsupported operator: %s' % op
                import sqlalchemy.sql
                op = getattr(sqlalchemy.sql, '%s_' % op)
                clause = op(prev_clause, clause)

            prev_clause = clause

            try:
                op = expr_iter.next()
            except StopIteration:
                pass

        return query.filter(clause)


    def search(self, text, session=None):
        '''
        return the search results depending on how tokens were parsed
        '''
        if session is None:
            session = bauble.Session()

        try:
            tokens = self.parser.parse_string(text)
        except:
            return []
        results = ResultSet()
        if 'values' in tokens:
#            debug('searching values')
            # make searches in postgres case-insensitive, i don't think other
            # databases support a case-insensitive like operator
            if bauble.engine.name == 'postgres':
                like = lambda table, col, val: \
                       table.c[col].op('ILIKE')('%%%s%%' % val)
            else:
                like = lambda table, col, val: \
                       table.c[col].like('%%%s%%' % val)
            for mapping, columns in self._mapping_columns.iteritems():
                q = session.query(mapping)
                cv = [(c,v) for c in columns for v in tokens['values']]

                # as of SQLAlchemy 0.4.2 we convert the value to a unicode
                # object if the col is a Unicode or UnicodeText column in order
                # to avoid the "Unicode type received non-unicode bind param"
                def unicol(col, v):
                    if isinstance(mapping.c[col].type, (Unicode,UnicodeText)):
                        return unicode(v)
                    else:
                        return v
                q =q.filter(or_(*[like(mapping,c,unicol(c, v)) for c,v in cv]))
                results.add(q)
        elif 'expression' in tokens:
            #debug(tokens.dump())
            for domain, cond, val in tokens:#['expression']:
##                 debug(tokens['expression'])
##                 debug(tokens.dump())
##                 debug(domain)
##                 debug(cond)
##                 debug(val)
                try:
                    mapping, columns = self._domains[domain]
                except KeyError:
                    raise KeyError(_('Unknown search domain: %s' % domain))
                query = session.query(mapping)
                # TODO: should probably create a normalize_cond() method
                # to convert things like contains and has into like conditions

                # TODO: i think that sqlite uses case insensitve like, there
                # is a pragma to change this so maybe we could send that
                # command first to handle case sensitive and insensitive
                # queries

                if cond in ('ilike', 'icontains') and \
                       bauble.engine.name != 'postgres':
                    msg = _('The <i>ilike</i> and <i>icontains</i> '\
                            'operators are only supported on PostgreSQL ' \
                            'databases. You are connected to a %s database.') \
                            % bauble.engine.name
                    utils.message_dialog(msg, gtk.MESSAGE_WARNING)
                    return results
                if cond in ('contains', 'icontains', 'has', 'ihas'):
                    val = '%%%s%%' % val
                    if cond in ('icontains', 'ihas'):
                        cond = 'ilike'
                    else:
                        cond = 'like'

                # select everything
                if val == '*':
                    results.add(query)
                else:
                    for col in columns:
                        results.add(query.filter(mapping.c[col].op(cond)(val)))
        elif 'query' in tokens:
            results.add(self._get_results_from_query(tokens, session))

        return results



class ResultSet(object):
    '''
    A ResultSet represents a set of results returned from a query, it
    allows you to add results to the set and then iterate over all the
    results as if they were one set.  It will only return objects that
    are unique between all the results.
    '''
    def __init__(self, results=None):
        if results is not None:
            self._results = set(results)
        else:
            self._results = set()


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
        # TODO: the problem we have with doing iteration this way is
        # that if this ResultSet contains other ResultSets that are
        # large we'll be creating lots of large set objects....of
        # course if the sets are really only holding references to the
        # objects then it might not be really be a problem
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



class SearchView(pluginmgr.View):

    class ViewMeta(dict):

        class Meta(object):
            def __init__(self):
                self.children = None
                self.infobox = None
                self.context_menu_desc = None
                self.markup_func = None


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
        statusbar.pop(sbcontext_id)
        results = ResultSet()
        error_msg = None
        self.session.clear() # clear out any old search results
        bold = '<b>%s</b>'
        try:
            for strategy in self.search_strategies:
                results.add(strategy.search(text, self.session))
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
            if len(results) > 1000:
                self.populate_results(results)
            else:
                task = self._populate_worker(results)
                while True:
                    try:
                        task.next()
                    except StopIteration:
                        break
                self.results_view.set_cursor(0)
            statusbar.pop(sbcontext_id)
            statusbar.push(sbcontext_id, _("%s search results") % len(results))



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
        except Exception, e:
            debug(e)
            debug(traceback.format_exc())
            return True
        else:
            self.append_children(model, iter, kids)
            return False


    def populate_results(self, results, check_for_kids=False):
        def on_error(exc):
            debug('SearchView.populate_results:')
            debug(exc)
        def on_quit():
            try:
                self.results_view.set_cursor(0)
            except Exception, e:
                debug(e)
        return bauble.task.queue(self._populate_worker, on_quit, on_error,
                                 results, check_for_kids)


    def _populate_worker(self, results, check_for_kids=False):
#    def populate_results(self, results, check_for_kids=False):
        nresults = len(results)
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1)
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        utils.clear_model(self.results_view)
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1)
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        # insert them into the model by groups
        groups = {}
        for key, group in itertools.groupby(results, lambda x: type(x)):
            groups[key] = group

        chunk_size = 100
        update_every = 1
        steps_so_far = 0
        for piece in utils.chunk(results, chunk_size):
            # TODO: the natural sort probably isn't compatible for non ASCII
            # character strings
            # TODO: choose between natsort_key or letting the returned results
            # determine the order....UPDATE 2008.02.28: stick with natsort
            # until we find something wrong with it...
            # UPDATE 2008.02.29: if sorting takes too long for large datasets
            # then maybe it would be better to
            #for obj in piece:
            for obj in sorted(piece, key=utils.natsort_key):
                parent = model.append(None, [obj])
                obj_type = type(obj)
                if check_for_kids:
                    kids = self.view_meta[obj_type].get_children(obj)
                    if len(kids) > 0:
                        model.append(parent, ['-'])
                elif self.view_meta[obj_type].children is not None:
                    model.append(parent, ['-'])

            steps_so_far += chunk_size
            if steps_so_far % update_every == 0:
                percent = float(steps_so_far)/float(nresults)
                if 0< percent < 1.0:
                    bauble.gui.progressbar.set_fraction(percent)
            yield
        self.results_view.freeze_child_notify()
        self.results_view.set_model(model)
        self.results_view.thaw_child_notify()


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
#        debug('%s(%s)' % (value, type(value)))
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
                    main = str(value)
                    substr = '(%s)' % type(value).__name__
                cell.set_property('markup', '%s\n%s' % \
                                  (_mainstr_tmpl % utils.utf8(main),
                                   _substr_tmpl % utils.utf8(substr)))

            except (saexc.InvalidRequestError, TypeError), e:
                debug(e)
                def remove():
                    treeview_model = self.results_view.get_model()
                    self.results_view.set_model(None) # detach model
                    for found in utils.search_tree_model(treeview_model,value):
                        #debug('remove: %' % str(model[found][0]))
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
        return all the rows in the model that are expanded
        '''
        expanded_rows = []
        self.results_view.map_expanded_rows(lambda view, path: expanded_rows.append(gtk.TreeRowReference(view.get_model(), path)))
        # seems to work better if we passed the reversed rows to
        # self.expand_to_all_refs
        expanded_rows.reverse()
        return expanded_rows


    def expand_to_all_refs(self, references):
        '''
        @param references: a list of TreeRowReferences to expand to

        Note: This method calls get_path() on each
        gtk.TreeRowReference in <references> which apparently
        invalidates the reference.
        '''
        for ref in references:
            if ref.valid():
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
                        result = False
                        try:
                            result = f(value)
                        except Exception, e:
                            msg = utils.xml_safe_utf8(str(e))
                            utils.message_details_dialog(msg,
                                                        traceback.format_exc(),
                                                         gtk.MESSAGE_ERROR)
                            debug(traceback.format_exc())
                        if result:
                            self.reset_view()
                    item = gtk.MenuItem(label)
                    item.connect('activate', on_activate, func)
                    menu.add(item)
            self.context_menu_cache[selected_type] = menu

        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)


    def reset_view(self):
        """
        expire all the children in the model, collapse everything,
        reexpand the rows to the previous state where possible and
        update the infobox
        """
        # TODO: we should do some profiling to see how this method
        # performs on large datasets
        model, paths = self.results_view.get_selection().get_selected_rows()
        ref = gtk.TreeRowReference(model, paths[0])
        for obj in self.session:
            try:
                self.session.expire(obj)
            except saexc.InvalidRequestError, e:
                    model.remove(found)
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

def select_in_search_results(obj):
    """
    @param obj: the object the select
    @returns: a gtk.TreeIter to the selected row

    search the tree model for obj if it exists then select it if not
    then add it and select it

    the the obj is not in the first level of the model then we add it
    """
    assert obj != None, 'select_in_search_results: arg is None'
    view = bauble.gui.get_view()
    if not isinstance(view, SearchView):
        return None
    model = view.results_view.get_model()
    found = utils.search_tree_model(model, obj)
    path = None
    row_iter = None
    if len(found) > 0:
        row_iter = found[0]
        path = model.get_path(row_iter)
    else:
        row_iter = model.append(None, [obj])
        model.append(row_iter, ['-'])
        path = model.get_path(row_iter)
    view.results_view.set_cursor(path)
    return row_iter


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

