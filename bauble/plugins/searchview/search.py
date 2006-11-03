#
# search.py
#

import re, traceback
import gtk, gobject, pango
from sqlalchemy import *
import sqlalchemy.exceptions as saexc
from sqlalchemy.orm.attributes import InstrumentedList
from sqlalchemy.orm.mapper import Mapper
import formencode
import bauble
import bauble.error as error
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.plugins.searchview.infobox import InfoBox
from bauble.plugins import BaubleView, tables, editors
from bauble.utils.log import debug
from pyparsing import *

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

# TODO: could push the search map into the table modules so each table can
# have its own search map thens this module doesn't have to know about all the 
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

# TODO: make the search entry a combo. clicking on the combo button
# pops up the previous X searches. the up and down arrows cycle through the 
# search history. the histories should be stored separately per connection, 
# possible in the BaubleMeta table. the X number of search to remember and 
# saving the searches per connection should be configurable

# TODO: search won't work on a unicode col. e.g. try 'acc where notes='test''

# TODO: improve error reporting, especially when there is an error in the
# search string or if there aren't any results
# e.g. 'Can't find 'values' in table 'Table'

# TODO: on some search errors the connection gets invalidated, this 
# happened to me on 'loc where site=test'
# UPDATE: this query doesn't invalidate the connection any more but apparantly
# there's a way that this happens so we should track it down

# TODO: it would be good to be able to search using the SIMILAR TO operator
# but we need to designate a way to show that value is a regular expression

# TODO: support '%' at from and end of string to do fuzzy searches, should
# really support any standard sql regex syntax like ?*, etc...

# TODO: try this syntax for AND and OR queries, this should make it easy
#a=Entries.select(AND(Entries.q.aCount==3,Entries.q.alpha==myalpha))

# TODO: create a set of commands from the search entry, e.g. :help or :config

class SearchParser:

    # TODO: if the search language doesn't change we could make this 
    # a static class, the only reason we wouldn't is if we made the values
    # in self.domain_map keywords

    def __init__(self):	
        '''
        the constructor
        '''
    	domain = Word(alphanums).setResultsName('domain')
    	quotes = Word('"\'')    
        
    	value_str_chars = alphanums + '*;.'
    	value_str = Word(value_str_chars)
    	quoted_value_str = Optional(quotes).suppress() + \
    	    Word(value_str_chars+' ') + Optional(quotes).suppress()
    	_values = delimitedList(value_str | quoted_value_str)
    	values = Group(_values).setResultsName('values')
    	
    	operator = oneOf('= == != <> < <= > >=').setResultsName('operator')
    	expression = domain + operator + values + StringEnd()
    
    	subdomain = Word(alphanums + '._').setResultsName('subdomain')
    	query_expression = (subdomain + operator + \
    			    values).setResultsName('query')
    
    	query = domain + CaselessKeyword("where").suppress() + subdomain + \
    	    operator + values + StringEnd()
    
    	self.statement = (query | expression | (values + StringEnd()))
		

    def parse_string(self, text):
        '''
        '''
        return self.statement.parseString(text)
	


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
    '''
    convert accepted parse operators to python operators
    NOTE: this operator validator is only for python operators and doesn't
    do convert operators that may be specific to the database type
    '''
    to_operator_map = {'=': '==', 
		       '<>': '!=',
		       }
		       	 

class SearchMeta:
    
    def __init__(self, table_name, column_names, sort_column=None, 
                 context_menu=None, markup_func=None):
        """
        @param table_name: the name of the table this meta refers to
        @param column_names: the names of the table columns that will be search
        @param sort: column to sort on, can use -column for descending order, this
            should also work if you do ["col1", "col2"]
        """        
        self.table = tables[table_name]
        if type(column_names) is not list:
            raise ValueError("SearchMeta.__init__: column_names must be a list")
        self.columns = column_names
        
        # TODO: if the the column is a join then it will sort by the id of the
        # joined objects rather than the values of the objects, we should check
        # if any of the columns passed are joins and handle them properly with
        # and AND() or something
        self.sort_column = sort_column 
        


class SearchView(BaubleView):
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
                @param context_menu: a dict describing the context menu used when the
                    user right clicks on this type
                @param markup_func: the function to call to markup search results of 
                    this type, if markup_func is None the instances __str__() function 
                    is called            
                '''
                self.children = children
#                self.editor = editor
                self.infobox = infobox
                self.context_menu_desc = context_menu
                self.markup_func = markup_func
        
        
            def get_children(self, so_instance):
                '''
                @param so_instance: get the children from so_instance according
                    to self.children
                '''
                if self.children is None:
                    return []
                tablename = so_instance.__class__.__name__            
                if callable(self.children):
                    return self.children(so_instance)

		        # TODO: need to get in the default sort order
                return getattr(so_instance, self.children)
        
            
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
        table_name = search_meta.table.__name__
        cls.domain_map[domain] = table_name
        cls.search_metas[table_name] = search_meta
  
  
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

        table_name = type(row).__name__
        new_infobox = None
        
        # check if we've already created an infobox of this type,
        # if not create one and put it in self.infobox_cache
        if table_name in self.infobox_cache.keys():
            new_infobox = self.infobox_cache[table_name]
        elif table_name in self.view_meta and \
          self.view_meta[table_name].infobox is not None:
            new_infobox = self.view_meta[table_name].infobox()
            self.infobox_cache[table_name] = new_infobox        
                
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


    def refresh_search(self):
        self.search_text = self.search_text        

    
    def _get_search_results_from_tokens(self, tokens):
        '''
        take list of tokens from parser.parseString() and return search
        results for them
        '''
#        debug('_get_search_results_from_tokens(%s)' % tokens)
        results = []            
        #session = create_session()
        if 'subdomain' in tokens and 'domain' in tokens: # a query expression    	        	
             # FIXME *****: this doesn't work if the one of the dotted columns
             # is not a backref, try searching for 
             # gen where family_id.qualifier='test'
    	    #operator = OperatorValidator.to_python(tokens['operator'])
    	    #operator = tokens['operator']
            joins = None
            col = None
    	    values = tokens['values']
    	    domain_table = tables[self.domain_map[tokens['domain']]]    	    
            subdomain = tokens['subdomain']    	    
            index = subdomain.rfind('.')            
    	    if index != -1:
                joins, col = subdomain[:index], subdomain[index+1:]
    	    else:
                col = subdomain		
            debug('joins: %s' % joins)
            debug('col: %s' % col)
    	    if joins is None: # select from column in domain_table
                # TODO: this is still fairly incomplete and doesn't allow
                # different operators
                query = self.session.query(domain_table)
                results = query.select(domain_table.c[col]==values[0])
#                debug(results)
                
                
#                # get the validator for the column
#                if col == 'id':
#                    values_validator = formencode.validators.Int()
#                elif col in domain_table.sqlmeta.columns:
#                    values_validator = \
#                    domain_table.sqlmeta.columns[col].validator()
#                else:
#                    raise KeyError('"%s" not a column in table "%s"' % \
#                                   (col, domain_table.__name__))
#                #v = values_validator.to_python(','.join(values), None)
#                v = values_validator.from_python(','.join(values), None)
#                if not isinstance(v, int):
#                    # quote if not an int
#                    v = sqlobject.sqlhub.processConnection.sqlrepr(_LikeQuoted(v))
#                #db_type = sqlobject.sqlhub.processConnection.dbName
#                db_type = bauble.app.db_engine.name
#                debug(db_type)
#                operator = tokens['operator']
#                sql_operator= SQLOperatorValidator(db_type).to_python(operator)                
#                debug(domain_table)
#                stmt = "%s.%s %s %s" % (domain_table,
#                                        col, sql_operator, v)
#                debug(stmt)
#                results += domain_table.select(stmt)
    	    else: 
                # resolve the joins and select from the last join in the list
                # TODO: would it be possible to do this backwards. if we could
                # get the type of the table of the last join on the list of 
                # subdomains we could then query this table for the value in 
                # col, this would allow us to walk up the list of joins until
                # we get to the top. it seems like this way would be alot more
                # efficient because you only get the values from the 
                # domain_table from the beginning instead of starting with
                # all values in domain tables and narrowing down from there
                # UPDATE: can we do this reliably if one the subdomains is 
                # a mapped property, i.e. relation and not a column
                # debug(eval('tables["%s"].%s.%s' % (domain_table.__name__, joins, col)))                
                joins = joins.split('.')
                backrefs = []
                next_class = domain_table
                for j in joins:          
                    if isinstance(next_class, Mapper):
                        relation = next_class.props[j]
                    else:
                        relation = class_mapper(next_class).props[j]
                    
                    backrefs.append(relation.backref.key)
                    next_class = relation.argument
                last_class = next_class
                debug('backrefs: %s' % backrefs)
                debug('last_class: %s' % last_class)
                
                debug('last_class.c: %s' % last_class.c)
                if isinstance(last_class, Mapper):
                    bottom_results = self.query_table(last_class.mapped_table, values[0])
                else:
                    bottom_results = self.session.query(last_class).select(last_class.c[col] == values[0])            
                    
                debug('bottom_results: %s' % bottom_results)
                # now walk back up
                for r in bottom_results: 
                    upper = None
                    for backref in backrefs:
                        try:
                            upper = upper.__getattribute__(backref)
                        except:
                            upper = r.__getattribute__(backref)
                    if upper is None: 
                        # shouldn't ever get here
                        raise ValueError('couldn\'t walk up back references')
                    #debug(type(upper))
                    if isinstance(upper, (list, tuple, InstrumentedList)):
                        map(self.session.save, upper)
                        if len(upper) > 0:
                            debug('extend: %s' % upper)
                            results.extend(upper)                    
                    else:
                        debug('append upper: %s' % upper)
                        self.session.save(upper)
                        results.append(upper)
        elif 'domain' in tokens and tokens['domain'] in self.domain_map: 
            # a general expression
            #values = ','.join(tokens['values']) # can values not be in tokens?
            values= tokens['values']
#            debug(values)	    
            table_name = self.domain_map[tokens['domain']]
            results += self.query_table(table_name, values)#[:]
        elif 'values' in tokens: # a list of values
            values = tokens['values']
            for table_name in self.search_metas.keys():
                results += self.query_table(table_name, values)[:]
        else:
            raise error.BaubleError('invalid tokens')
        return results
        
        
    nresults_statusbar_context = 'searchview.nresults'
    
    def search(self, text):
        '''
        search the database using text
        '''
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from 
        # outside the class so the entry and search results match
        self.entry.set_text(text)
        self._search_text = text            
        
        # clear the old model
        set_cursor = bauble.app.gui.window.window.set_cursor
        set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        #bauble.app.set_busy(True)
        self.results_view.set_model(None)      
        statusbar = bauble.app.gui.statusbar        
        sbcontext_id = statusbar.get_context_id('searchview.nresults')
        results = []
        error_msg = None
        self.session.clear() # clear out any old search results
        try:
    	    tokens = self.parser.parse_string(text)	    
            if 'domain' in tokens and tokens.domain not in self.domain_map:
                raise SyntaxError("Unknown search domain: %s" % tokens.domain)
    	    results = self._get_search_results_from_tokens(tokens)
        except ParseException, err:
            error_msg = 'Error in search string at column %s' % err.column
        except (error.BaubleError, AttributeError, Exception, SyntaxError), e:
            debug(traceback.format_exc())
            error_msg = '** Error: %s' % utils.xml_safe(e)
                    
        if len(results) == 0:
            model = gtk.ListStore(str)
            if error_msg is not None:
                model.append([error_msg])
            else:
                model.append(["Couldn't find anything"])
            statusbar.pop(sbcontext_id)            
            self.results_view.set_model(model)            
            set_cursor(None)
            #bauble.app.set_busy(False)
        else:
            def populate_callback():
                self.populate_results(results)
                statusbar.push(sbcontext_id, "%s results" % len(results))  
                set_cursor(None)
                #bauble.app.set_busy(False)
            if len(results) > 2000:
                msg = 'This query returned %s results.  It may take a '\
                        'long time to get all the data. Are you sure you want to '\
                        'continue?' % len(results)
                if utils.yes_no_dialog(msg):                    
                    gobject.idle_add(populate_callback)
                else:
                    set_cursor(None)
            else:
	    		gobject.idle_add(populate_callback)
        

    def remove_children(self, model, parent):
        '''
        remove all children of some parent in the model, reverse
        iterate through them so you don't invalidate the iter
        '''
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

        table_name = type(row).__name__
        kids = self.view_meta[table_name].get_children(row)
        if len(kids) == 0:
            return True
        self.append_children(model, iter, kids, True)
        return False
        
                    
    def query_table(self, table_name, values):
        '''
        query the table table_name for values which are 'OR'ed together    
        
        @param table_name: the table_name should be registered in search_meta
        @param svalues: list of values to query table_name
        '''
        if table_name not in self.search_metas:
            raise ValueError("SearchView.query: no search meta for domain ", 
                              domain)
        search_meta = self.search_metas[table_name]
        table = search_meta.table
        columns = search_meta.columns
        query = self.session.query(table)
        
        # select everything
        if values[0] in ('*', 'all'):            
            return query.select()

        # select like
        if bauble.app.db_engine.name == 'postgres':
            s = query.select(or_(*[table.c[columns[0]].op('ILIKE')('%%%s%%' % v) for v in values]))
        else:            
            s = query.select(or_(*[table.c[columns[0]].like('%%%s%%' % v) for v in values]))
        return s
        
        	            

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
            if check_for_kids:
                kids = self.view_meta[s.__class__.__name__].get_children(s)            
                if len(kids) > 0:                
                    model.append(p, ['-'])        
            else:
                model.append(p, ['-'])             
        self.results_view.freeze_child_notify()
        self.results_view.set_model(model)	
        self.results_view.thaw_child_notify()
	        
    
    def append_children(self, model, parent, kids, have_kids):
        '''
        append object to a parent iter in the model        
        
        @param model: the model the append to
        @param parent:  the parent iter
        @param kids: a list of kids to append
        @param have_kids: whether we should add a dummy indicator that the appended
            kids have kides        
        @return: the model with the kids appended
        '''
        if parent is None:
            raise Exception("need a parent")
        for k in kids:
            i = model.append(parent, [k])
            if have_kids:
                model.append(i, ["_dummy"])
        return model
       
    
    def cell_data_func(self, coll, cell, model, iter):    
        value = model[iter][0]
        table_name = value.__class__.__name__
        func = self.view_meta[table_name].markup_func        
        try:        
            cell.set_property('markup', func(value))
        except:
            try:
                cell.set_property('markup', '<b>%s</b>\n<small>(%s)</small>' % (value, type(value).__name__))
            except TypeError, saexc.InvalidRequestError: 
                # remove it from the results list if we can't 
                # display, most like it was removed from the database
#                cell.set_property('text', '<bad value>')
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
        # the model(or what if it doesn't) and the view has to be refreshed from 
        # a large dataset
        if event.button != 3: 
            return # if not right click then leave
        
        sel = view.get_selection()
        model, i = sel.get_selected()
        if model == None:
            return # nothing to pop up a context menu on
        value = model[i][0]
        
        path = model.get_path(i) # get the path to pass to the callback
        
        table_name = value.__class__.__name__
        if self.view_meta[table_name].context_menu_desc is None:            
            # no context menu
            return        
        
        menu = None
        try:
            menu = self.context_menu_cache[table_name]
        except:
            menu = gtk.Menu()
            for label, func in self.view_meta[table_name].context_menu_desc:
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
                                    # find the object in the tree and remove it,
                                    # this could get expensive if there are a
                                    # lot of items in the tree                                    
                                    for found in utils.search_tree_model(model, obj):
#                                        debug('found %s: %s' % (found, model[found][0]))
                                        model.remove(found)
                            self.results_view.collapse_all()
                            self.expand_to_all_refs(expanded_rows)         
                            self.update_infobox()                            

                    item = gtk.MenuItem(label)                    
                    item.connect('activate', on_activate, func, model, path)
                    menu.add(item)
            self.context_menu_cache[table_name] = menu
        
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
        self.content_box = gtk.VBox()  
                  
        # create the entry and search button
        self.entry = gtk.Entry()
    	#self.combo_entry = gtk.combo_box_entry_new_text()
    	#self.entry = combo_entry.entry
        self.entry.connect("key_press_event", self.on_entry_key_press)
        
        self.search_button = gtk.Button("Search")
        self.search_button.connect("clicked", self.on_search_button_clicked)
                
        entry_box = gtk.HBox() # hold the search entry and search_button
        entry_box.pack_start(self.entry, True, True, 5)
        entry_box.pack_end(self.search_button, False, False, 5)
        self.content_box.pack_start(entry_box, False, False, 5)
        
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
        #pane_box = gtk.HBox(False)
        #pane_box.pack_start(self.pane, True, True)
        #self.content_box.pack_start(self.pane, True, True)
        
        # add the GBIFView 
        # create the expander but don't create the GBIFView object unless
        # it's expanded, should later remove the view or at least disable
        # it if the expander is collapsed
        
        # ** temporarily remove the gbif expander
        #self.gbif_expand = gtk.Expander("Online Search")
        #self.gbif_expand.connect("activate", self.on_activate_gbif_expand)
        #self.gbif_expand.set_expanded(False)
        #vpane = gtk.VPaned()
        #vpane.pack1(pane_box, True, True)
        #vpane.pack2(self.gbif_expand, True, True)
        #self.content_box.pack_start(vpane, True, True)
        
        #self.content_box.pack_start(pane_box)
        self.content_box.pack_start(self.pane)        
        self.add(self.content_box)

        # add accelerators
        accel_group = gtk.AccelGroup()
        self.entry.add_accelerator("grab-focus", accel_group, ord('L'),
                                   gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
        bauble.app.gui.window.add_accel_group(accel_group)
        self.show_all()
        

#    def on_activate_gbif_expand(self, expander, data=None):
#        '''
#        '''
#        expanded = expander.get_expanded()
#        gbif = expander.get_child()
#        # this is fired before the expanded state is set so we should assume
#        # that if this is fired the opposite is being done. e.g. if it is 
#        # activate and is currently expanded we should assume it us being
#        # collapsed
#        if not expanded and gbif is None:
#            gbif = views.views.GBIFView(bauble)
#            expander.add(gbif)
#        elif gbif is not None:
#            expander.remove(gbif)
            
        
    # TODO: should i or should i not delete everything that is a child
    # of the row when it is collapsed, this would save memory but
    # would cause it to be slow if rows were collapsed and need to be
    # reopend
#    def on_row_collapsed(self, view, iter, path, data=None):
#        '''        
#        '''
#        pass
       

