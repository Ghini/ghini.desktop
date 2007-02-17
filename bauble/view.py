#
# view.py
#
# Description: the default view
#
import sys, re, traceback
import gtk, gobject, pango
from sqlalchemy import *
import sqlalchemy.exceptions as saexc
from sqlalchemy.orm.attributes import InstrumentedList
from sqlalchemy.orm.mapper import Mapper
import formencode
import bauble
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

# TODO: make the search result do their thing in a task so we can keep state and
# pulse the progressbar for large result sets

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
        gtk.Expander.__init__(self, label)
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
        gtk.ScrolledWindow.__init__(self)
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


class SearchParser:
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
        domain = Word(alphas, alphanums)
        
        and_ = CaselessKeyword("and")
        or_ = CaselessKeyword("or")
        in_ = CaselessKeyword("in")
        like = CaselessKeyword('like')
        # should provide a warning on non-postgres database
        ilike = CaselessKeyword('ilike') 
        contains = CaselessKeyword("contains") # TODO: does like('%%%s%%')
        
        valuechars = alphanums + '*;._-%'
        quoted_value = quotes.suppress() + Word(valuechars+' ') + \
                       quotes.suppress()
        value = Word(valuechars)# | quoted_value
        delimited_values = delimitedList(Word(valuechars))
        values = delimitedList(value | quoted_value)#.setResultsName('values')
        
        binop = oneOf('= == != <> < <= > >= not')#.setResultsName('operator') 
        domain_expression = domain + (binop | like | ilike) + values
            
        identifier = Word(alphas, alphanums + "._")#.setName("identifier")
        where = CaselessKeyword('where')
        where_condition = Group(identifier + (binop|like|ilike) + values)
        where_expression = where.suppress() + where_condition + \
                           ZeroOrMore((and_ | or_) + where_condition)
        query = domain + Group(where_expression)#.setResultsName('expression')
        
        self.statement = (query.setResultsName('query') | \
                          domain_expression.setResultsName('expression') | \
                          (values + StringEnd()).setResultsName('values'))
        
    def parse_string(self, text):
        '''
        '''
        return self.statement.parseString(text)
        
#class SearchParser:
#
#    # TODO: if the search language doesn't change we could make this 
#    # a static class, the only reason we wouldn't is if we made the values
#    # in self.domain_map keywords
#
#    def __init__(self):    
#        '''
#        the constructor
#        '''
#        domain = Word(alphanums).setResultsName('domain')
#        quotes = Word('"\'')    
#        
#        value_str_chars = alphanums + '*;._-'
#        value_str = Word(value_str_chars)
#        quoted_value_str = Optional(quotes).suppress() + \
#            Word(value_str_chars+' ,') + Optional(quotes).suppress()
#        _values = delimitedList(value_str | quoted_value_str)
#        values = Group(_values).setResultsName('values')
#        
#        operator = oneOf('= == != <> < <= > >=').setResultsName('operator')
#        expression = domain + operator + values + StringEnd()
#    
#        subdomain = Word(alphanums + '._').setResultsName('subdomain')
#        query_expression = (subdomain + operator + \
#                    values).setResultsName('query')
#    
#        query = domain + CaselessKeyword("where").suppress() + subdomain + \
#            operator + values + StringEnd()
#    
#        self.statement = (query | expression | (values + StringEnd()))
#        
#
#    def parse_string(self, text):
#        '''
#        '''
#        return self.statement.parseString(text)
    


class OperatorValidator(formencode.FancyValidator):

    to_operator_map = {}

    def _to_python(self, value, state=None):
        if value in self.to_operator_map:
            return self.to_operator_map[value]
        else:
            return value


    def _from_python(self, value, state=None):
        return value


class SQLOperatorValidator(OperatorValidator):

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


class PythonOperatorValidator(OperatorValidator):
    """
    convert accepted parse operators to python operators
    NOTE: this operator validator is only for python operators and doesn't
    do convert operators that may be specific to the database type
    """
    to_operator_map = {'=': '==', 
               '<>': '!=',
               }
                    
class SearchMeta:
    
    def __init__(self, mapper, columns, context_menu=None, markup_func=None):
        """
        @param mapper: a Mapper object
        @param columns: the names of the table columns that will be search
        @parem context_menu:
        @param markup_func:
        """
        self.mapper = class_mapper(mapper)
        assert isinstance(columns, list), 'SearchMeta.__init__: '\
                                          'columns argument must be a list'
        self.columns = columns



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
    
    class ViewMeta(dict):

        class Meta:
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

                # TODO: need to get in the default sort order
                return getattr(obj, self.children)
        
            
        def __getitem__(self, item):
            if item not in self: # create on demand
                self[item] = self.Meta()
            return self.get(item)
            
    view_meta = ViewMeta()
    
    
    @classmethod
    def register_search_meta(cls, domain, search_meta):        
        '''
        @param domain: a shorthand for for queries for this class
        @param search_meta: the meta information to register with the domain
        '''
        table_name = search_meta.mapper.local_table.name
        cls.domain_map[domain] = search_meta.mapper
        # look up by name of mapped class
        cls.search_metas[search_meta.mapper.class_.__name__] = search_meta
  
    
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
        sel = self.results_view.get_selection() # get the selected row
        model, it = sel.get_selected()
        value = None
        if it is not None:
            value = model[it][0]            
        try:
            self.set_infobox_from_row(value)
        except Exception, e:
            debug('SearchView.update_infobox: %s' % e)
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
            


    def get_selected(self):
        '''
        return all the selected rows
        '''
        model, rows = self.results_view.get_selection().get_selected_rows()
        selected = []
        for row in rows:
            selected.append(model[row][0])
        return selected
        

    def on_results_view_select_row(self, view):
        '''
        add and removes the infobox which should change depending on
        the type of the row selected
        '''
        self.update_infobox()
        
        # check that the gbif view is expanded
        # if it is then pass the selected row to gbif
        #if self.gbif_expand.get_expanded():
        #    gbif = self.gbif_expand.get_child()
        #    gbif.search(value)
        
    
    def on_search_button_clicked(self, widget):
        '''
        '''
        text = self.entry.get_text()
        self.search_text = text
        # the row has been unselected, so turn off the infobox
        self.set_infobox_from_row(None) 
        

    # search text property: setting self.search_text resets the view and
    # automatically searches for the text unless you set it to '' or None
    _search_text = None
    def _get_search_text(self):
        return self._search_text
    def _set_search_text(self, text):
        self.reset()
        self._search_text = text or ''
        self.entry.set_text(self._search_text)
        if self._search_text != '':
            self.search(self._search_text)
    search_text = property(_get_search_text, _set_search_text)


    def reset(self):
        self._search_text = None
        self.entry.set_text('')
        self.results_view.set_model(None)
        self.set_infobox_from_row(None)
        self.session.clear()


    def refresh_search(self):
        self.search_text = self.search_text        

    condition_map = {'and': and_, 
                     'or': or_}
    
    def _get_search_results_from_tokens(self, tokens):        
        # TODO: need to support joins so that queries like
        # species where genus=Maxillaria and sp=aciantha would return
        # the species Maxillaria aciantha        
        # TODO: need to support 'or'ing values for queries and expression
#        debug('tokens: %s' % tokens)
        results = []        
        if 'query' in tokens:      
            domain = str(tokens[0])
            try:
                mapping = self.domain_map[domain]
            except KeyError, e:
                raise KeyError('Unknown domain: %s' % domain)
                
            query = self.session.query(mapping)
            table = mapping.local_table
            
            #debug('domain: %s' % domain)
            expression = tokens[1]
            #'test=val and test=val and test=val or test=val'
            #'test=val and (test=val or test=val)
            #debug('expression: %s' % expression)            
            col, cond, val = expression[0]
            assert col in table.c, \
                   _('Unknown column "%s" on table "%s"') % (col, table.name)
            prev_expr = table.c[col].op(cond)(val)
            debug((col, cond, val))            
            ops = expression[1:][::2]
            ex = expression[1:][1::2]            
            for op, [col, cond, val] in zip(ops, ex):
                assert col in table.c, \
                       _('Unknown column "%s" on table "%s"') %(col,table.name)
#                debug('%s, %s, %s, %s' % (op, col, cond, val))
                prev_expr = self.condition_map[op](prev_expr, table.c[col].op(cond)(val))            
#            debug('expr: %s -- %s' % (prev_expr, repr(prev_expr)))        
            results = query.select(prev_expr)
#            debug('s: %s' % results)

        elif 'expression' in tokens:
            domain, cond, val = tokens['expression']
#            debug('expression: %s, %s, %s' % (domain, cond, val))
            mapping = self.domain_map[domain]
            search_meta = self.search_metas[mapping.__class__.__name__]
            query = self.session.query(mapping)
            if cond == 'ilike' and bauble.db_engine.name != 'postgres':
                utils.message_dialog('The ilike operator is only supported ' \
                                     'on PostgreSQL database. You are ' \
                                     'connected to a %s database' \
                                     % bauble.db_engine.name,
                                     gtk.MESSAGE_WARNING)
                return []            
            # select everything
            if val in ('*', 'all'):            
                results = query.select()
            else:
                for col in search_meta.columns:
                    results.extend(query.select(mapping.c[col].op(cond)(val)))
        else:            
#            debug('is an value')
            # make searches in postgres case-insensitive, i don't think other 
            # databases support a case-insensitive like operator
            if bauble.db_engine.name == 'postgres': 
                like = lambda table, col, val: \
                       table.c[col].op('ILIKE')('%%%s%%' % val)
            else:
                like = lambda table, col, val: \
                       table.c[col].like('%%%s%%' % val)
                                
            for meta in self.search_metas.values():
                mapping = meta.mapper
                q = self.session.query(mapping)
                cv = [(c,v) for c in meta.columns for v in tokens]
                results.extend(q.select(or_(*[like(mapping, c, v) for c,v in cv])))        
        return results
    
#    def _get_search_results_from_tokens_old(self, tokens):
#        '''
#        take list of tokens from parser.parseString() and return search
#        results for them
#        '''
##        debug('_get_search_results_from_tokens(%s)' % tokens)
#        results = []            
#        #session = create_session()
#        if 'subdomain' in tokens and 'domain' in tokens: # a query expression                    
#             # FIXME *****: this doesn't work if the one of the dotted columns
#             # is not a backref, try searching for 
#             # gen where family_id.qualifier='test'
#            #operator = OperatorValidator.to_python(tokens['operator'])
#            #operator = tokens['operator']
#            joins = None
#            col = None
#            values = tokens['values']
#            domain_table = tables[self.domain_map[tokens['domain']]]            
#            subdomain = tokens['subdomain']            
#            index = subdomain.rfind('.')            
#            if index != -1:
#                joins, col = subdomain[:index], subdomain[index+1:]
#            else:
#                col = subdomain        
#            debug('joins: %s' % joins)
#            debug('col: %s' % col)
#            if joins is None: # select from column in domain_table
#                # TODO: this is still fairly incomplete and doesn't allow
#                # different operators
#                query = self.session.query(domain_table)
#                results = query.select(domain_table.c[col]==values[0])
##                debug(results)
#                
#                
##                # get the validator for the column
##                if col == 'id':
##                    values_validator = formencode.validators.Int()
##                elif col in domain_table.sqlmeta.columns:
##                    values_validator = \
##                    domain_table.sqlmeta.columns[col].validator()
##                else:
##                    raise KeyError('"%s" not a column in table "%s"' % \
##                                   (col, domain_table.__name__))
##                #v = values_validator.to_python(','.join(values), None)
##                v = values_validator.from_python(','.join(values), None)
##                if not isinstance(v, int):
##                    # quote if not an int
##                    v = sqlobject.sqlhub.processConnection.sqlrepr(_LikeQuoted(v))
##                #db_type = sqlobject.sqlhub.processConnection.dbName
##                db_type = bauble.app.db_engine.name
##                debug(db_type)
##                operator = tokens['operator']
##                sql_operator= SQLOperatorValidator(db_type).to_python(operator)                
##                debug(domain_table)
##                stmt = "%s.%s %s %s" % (domain_table,
##                                        col, sql_operator, v)
##                debug(stmt)
##                results += domain_table.select(stmt)
#            else: 
#                # resolve the joins and select from the last join in the list
#                # TODO: would it be possible to do this backwards. if we could
#                # get the type of the table of the last join on the list of 
#                # subdomains we could then query this table for the value in 
#                # col, this would allow us to walk up the list of joins until
#                # we get to the top. it seems like this way would be alot more
#                # efficient because you only get the values from the 
#                # domain_table from the beginning instead of starting with
#                # all values in domain tables and narrowing down from there
#                # UPDATE: can we do this reliably if one the subdomains is 
#                # a mapped property, i.e. relation and not a column
#                # debug(eval('tables["%s"].%s.%s' % (domain_table.__name__, joins, col)))                
#                joins = joins.split('.')
#                backrefs = []
#                next_class = domain_table
#                for j in joins:          
#                    if isinstance(next_class, Mapper):
#                        relation = next_class.props[j]
#                    else:
#                        relation = class_mapper(next_class).props[j]
#                    
#                    backrefs.append(relation.backref.key)
#                    next_class = relation.argument
#                last_class = next_class
#                debug('backrefs: %s' % backrefs)
#                debug('last_class: %s' % last_class)
#                
#                debug('last_class.c: %s' % last_class.c)
#                if isinstance(last_class, Mapper):
#                    bottom_results = self.query_table(last_class.mapped_table, values[0])
#                else:
#                    bottom_results = self.session.query(last_class).select(last_class.c[col] == values[0])            
#                    
#                debug('bottom_results: %s' % bottom_results)
#                # now walk back up
#                for r in bottom_results: 
#                    upper = None
#                    for backref in backrefs:
#                        try:
#                            upper = upper.__getattribute__(backref)
#                        except:
#                            upper = r.__getattribute__(backref)
#                    if upper is None: 
#                        # shouldn't ever get here
#                        raise ValueError('couldn\'t walk up back references')
#                    #debug(type(upper))
#                    if isinstance(upper, (list, tuple, InstrumentedList)):
#                        map(self.session.save, upper)
#                        if len(upper) > 0:
#                            debug('extend: %s' % upper)
#                            results.extend(upper)                    
#                    else:
#                        debug('append upper: %s' % upper)
#                        self.session.save(upper)
#                        results.append(upper)
#        elif 'domain' in tokens and tokens['domain'] in self.domain_map: 
#            # a general expression
#            #values = ','.join(tokens['values']) # can values not be in tokens?
#            values= tokens['values']
##            debug(values)        
#            table_name = self.domain_map[tokens['domain']]
#            results += self.query_table(table_name, values)#[:]
#        elif 'values' in tokens: # a list of values
#            values = tokens['values']
#            debug('list of values in tokens: %s' % values)
#            for table_name in self.search_metas.keys():
#                results += self.query_table(table_name, values)[:]
#        else:
#            raise error.BaubleError('invalid tokens')
#        return results
        
        
    nresults_statusbar_context = 'searchview.nresults'
    
    def search(self, text):
        '''
        search the database using text
        '''                
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from 
        # outside the class so the entry and search results match
        self.session.clear()
        #self.entry.set_text(text)
        self._search_text = text      
#        set_cursor = bauble.app.gui.window.window.set_cursor
#        set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))      
        
        # clear the old model    
        self.results_view.set_model(None)      
        statusbar = bauble.gui.widgets.statusbar
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        results = []
        error_msg = None
        self.session.clear() # clear out any old search results
        bold = '<b>%s</b>'        
        try:
            tokens = self.parser.parse_string(text)
            results = self._get_search_results_from_tokens(tokens)
#            debug('results: %s' % results)
        except ParseException, err:
            error_msg = 'Error in search string at column %s' % err.column
        except (error.BaubleError, AttributeError, Exception, SyntaxError), e:
            debug(traceback.format_exc())
            error_msg = '** Error: %s' % utils.xml_safe(e)
                    
        if len(results) == 0:
            model = gtk.ListStore(str)
            if error_msg is not None:
                model.append([bold % error_msg])
            else:
                model.append([bold % 'Couldn\'t find anything'])
            statusbar.pop(sbcontext_id)            
            self.results_view.set_model(model)            
#            set_cursor(None)
        else:
            def populate_callback():
                self.populate_results(results)
                statusbar.push(sbcontext_id, "%s results" % len(results))  
#                set_cursor(None)
            if len(results) > 2000:
                msg = 'This query returned %s results.  It may take a '\
                        'long time to get all the data. Are you sure you '\
                        'want to continue?' % len(results)
                if utils.yes_no_dialog(msg):                    
                    gobject.idle_add(populate_callback)
                else:
                    pass
#                    set_cursor(None)
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
        
                    
#    def query_table(self, table_name, values):
#        '''
#        query the table table_name for values which are 'OR'ed together    
#        
#        @param table_name: the table_name should be registered in search_meta
#        @param svalues: list of values to query table_name
#        '''
#        if table_name not in self.search_metas:
#            raise ValueError("SearchView.query: no search meta for domain ", 
#                              domain)
#        search_meta = self.search_metas[table_name]
##        table = search_meta.table
##        columns = search_meta.columns
##        query = self.session.query(table)
#        table = search_meta.mapper
#        query = self.session.query(table)
#        columns = search_meta.columns
#        
#        
#        # select everything
#        if values[0] in ('*', 'all'):            
#            return query.select()
#
#        # make searches in postgres case-insensitive, i don't think other 
#        # databases support a case-insensitive like operator
#        if bauble.db_engine.name == 'postgres': 
#            like = lambda col, val: table.c[col].op('ILIKE')('%%%s%%' % val)
#        else:
#            like = lambda col, val: table.c[col].like('%%%s%%' % val)
#                    
#        cv = [(c,v) for c in columns for v in values]
#        return query.select(or_(*[like(c, v) for c,v in cv]))
        
                        

#
# this is a version of populate_results using timeouts, it eventually bails 
# starts to slowdown and and so with the timeout it winds up not being that
# good anyways
#
    
#    def populate_results(self, select):
#        if self.populate_callback_id is not None:
#            gobject.source_remove(self.populate_callback_id)
#        results = []
#        model = self.results_view.get_model()
#        self.results_view.set_model(None) # temporarily remove the model
#        model = gtk.TreeStore(object)
#        model.set_default_sort_func(lambda *args: -1) 
#        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
#        
#        def idle_callback():
#            def append_select(select):
#                for s in select:
#                    p = model.append(None, [s])
#                    model.append(p, ['-'])            
#            slice_size = 100
#            timeout = 500 # in milliseconds
#            if len(select) < slice_size:
#                append_select(select)
#            else:
#                current = slice_size                
#                append_select(select[0:slice_size])
#                total_size = len(select)
#                def timeout_callback(curr):
#                    current = curr[0]
#                    the_end = False
#                    if current+slice_size > total_size:
#                        the_end = True
#                        sr = select[current:total_size-1]
#                    else:
#                        sr = select[current:current+slice_size]
#                    append_select(sr)
#                    curr[0] += slice_size
#                    if the_end:
#                        self.results_view.thaw_child_notify()
#                    return not the_end
#                self.populate_callback_id = gobject.timeout_add(timeout, timeout_callback, [current])
#        gobject.idle_add(idle_callback)
#        self.results_view.freeze_child_notify()
#        self.results_view.set_model(model)
        
        
    def populate_results(self, select, check_for_kids=False):
        '''
        populate the results view with the rows in select
        
        @param select: an iterable object to get the rows from
        @param check_for_kids: whether we should check if each of the rows in 
            select have children and set the expand indicator as such, this can
            signicantly slow down large lists of data, if this is False then all
            appended rows will have an expand indicator and the children will 
            be check on expansion
        '''
        results = []        
        model = self.results_view.get_model()
        self.results_view.set_model(None) # temporarily remove the model
        model = gtk.TreeStore(object)
        model.set_default_sort_func(lambda *args: -1) 
        model.set_sort_column_id(-1, gtk.SORT_ASCENDING)
        for s in select:
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
                cell.set_property('markup', '%s\n%s' % (_mainstr_tmpl % main, 
                                                        _substr_tmpl % substr))
            except (saexc.InvalidRequestError, TypeError), e:
                def remove():                    
                    treeview_model = self.results_view.get_model()
                    self.results_view.set_model(None)
                    for found in utils.search_tree_model(treeview_model, value):
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
        # TODO: SLOW -- it can be really slow if the the callback method changes
        # the model(or what if it doesn't) and the view has to be refreshed
        # from a large dataset
        if event.button != 3: 
            return # if not right click then leave
        
        sel = view.get_selection()
        model, i = sel.get_selected()
        if model == None:
            return # nothing to pop up a context menu on
        value = model[i][0]        
        selected_type = type(value)
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
                    def on_activate(item, f, model, iter):
                        expanded_rows = self.get_expanded_rows()
                        sel = view.get_selection()
                        model, treeiter = sel.get_selected()
                        if f(model[treeiter]) is not None:
                            for obj in self.session:
                                try:
                                    self.session.expire(obj)
#                                    obj.id
                                except saexc.InvalidRequestError:
#                                    debug('exception on refresh')
                                    # find the object in the tree and remove
                                    # it, this could get expensive if there
                                    # are a lot of items in the tree
                                    for found in utils.search_tree_model(model, obj):
#                                        debug('found %s: %s' % (found, model[found][0]))
                                        model.remove(found)
                            self.results_view.collapse_all()
                            self.expand_to_all_refs(expanded_rows)         
                            self.update_infobox()                            

                    item = gtk.MenuItem(label)
                    path = model.get_path(i)
                    item.connect('activate', on_activate, func, model, path)
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
       

# TODO: this should act like the search view and called when no other
# commands are matched from the command entry
class DefaultView(pluginmgr.View):
    
    def search(self, arg):
        debug('DefaultView.search(%s)' % arg)
    
    
class DefaultCommandHandler(pluginmgr.CommandHandler):
    
    command = None
 
    def get_view(self):
        self.view = SearchView()
        return self.view
    
    def __call__(self, arg):
        self.view.search(arg)
