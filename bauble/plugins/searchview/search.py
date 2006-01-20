#
# search.py
#

import re, traceback
import gtk
import sqlobject
import bauble
import bauble.utils as utils
from bauble.prefs import prefs
from bauble.plugins.searchview.infobox import InfoBox
from bauble.plugins import BaubleView, BaubleTable, tables, editors
from bauble.utils.log import debug
from pyparsing import *
#from earthenware.gui.pgtk.easygrid import EasyGrid


# NOTE: to add a new search domain do:
# 1. add table to search map with columns to search
# 2. add domain keys to domain map
# 3. if you want a result to expand on one of its children then
#    add the table and the default child to child_expand_map

# TODO: whenever an editor is called and changes are commited we should get 
# a list of expanded paths and then search again on the same criteria and then
# reexpand the paths that were saved and the path of the item that was the 
# editor was called on

# TODO: things todo when a result is selected
# - GBIF search results, probably have to look up specific institutions
# - search Lifemapper for distributions maps
# - give list of references and images and make then clickable if they are uris

# TODO: could push the search map into the table modules so each table can
# have its own search map thens this module doesn't have to know about all the 
# tables, it only has to query the tables module for the search map for all 
# tables, could also do something similar to domain map and child expand
# map

# TODO: as part of the view meta we should pass some sort table/map
# to build the context menu for a particular type with 
# (icon, label, callback(row)) or something of the sort, this would allow
# plugins to better control their behavior within the search view, in fact
# we would need a list of these and someway to include separators so there
# could be multiple menu items in the context menu, could also probably 
# replicate the context menu in the menu bar as well

# TODO: should check out TreeView.map_expanded_rows to get all the 
# expanded rows and then maybe we can reexpand them after we've 
# finished refreshing the view

# TODO: i don't really think that the sort column is that necessary
# in the SearchMeta since we have to sort all the results later, though
# if the results are partially sorted when we get them it make make them
# much faster to sort later, this would be worth looking into, we could also
# use the sort_column as the column to compare in the sorted method of
# populate_results

# TODO: provide a way to pin down the infobox so that changing the selection
# in the results_view doesn't change the values in the infobox

class SearchMeta:
    
    def __init__(self, table_name, column_names, sort_column=None):
        """
        table_name: the name of the table this meta refers to
        column_names: the names of the table columns that will be search
        sort: column to sort on, can use -column for descending order, this
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
    4. search specifically by family, genus, sp, isp(x?), author,
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
                
            def set(self, children=None, editor=None, infobox=None):
                self.children = children
                self.editor = editor
                self.infobox = infobox
        
        
            def get_children(self, so_instance):
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
        table_name = search_meta.table.__name__
        cls.domain_map[domain] = table_name
        cls.search_metas[table_name] = search_meta
  
  
    def __init__(self):
        #views.View.__init__(self)
        super(SearchView, self).__init__()
        self.create_gui()
        #self.entry.grab_focus() # this doesn't seem to work

    
    def set_infobox_from_row(self, row):    
#        return    
        if not hasattr(self, 'infobox'):
            self.infobox = None
        
        # TODO: check the class of the current infobox and if it matches
        # the class of the infobox we want to add then just update the values
        # instead of removing the infobox 
        
        # remove the old infobox
        if self.infobox is not None:
            if self.infobox.parent == self.pane:
                self.pane.remove(self.infobox)
		# had temporary disabled this in case it was causing a crash 
		# but, not i don't think it is
		self.infobox.destroy() 

        # row is  an object instance not a class so we have to get the class
        # and then the name to look it up in self.view_meta
        table_name = type(row).__name__
        if table_name in self.view_meta and \
          self.view_meta[table_name].infobox is not None:
            self.infobox = self.view_meta[table_name].infobox()
            if row is not None:
                self.infobox.update(row)
            self.pane.pack2(self.infobox, False, True)
        self.pane.show_all() # reset the pane


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
        """
        add and removes the infobox which should change depending on
        the type of the row selected
        """      
        sel = view.get_selection() # get the selected row
        model, i = sel.get_selected()
        value = model.get_value(i, 0)
        
        self.set_infobox_from_row(value)
        
        # check that the gbif view is expanded
        # if it is then pass the selected row to gbif
        #if self.gbif_expand.get_expanded():
        #    gbif = self.gbif_expand.get_child()
        #    gbif.search(value)
        
    
    def on_search_button_clicked(self, widget):
        text = self.entry.get_text()
        self.current_search_text = text
        self.search(text)
	# the row has been unselected, so turn off the infobox
	self.set_infobox_from_row(None) 
        
    
    # should be the search string relevant to the results in the results view
    current_search_text = None
 
# TODO: I think we should have a way to clear the search results, especially 
# while creating a new database   
#    def clear_search(self):
#        pass
    
    def refresh_search(self):
        if self.current_search_text is not None:
            self.search(self.current_search_text)
        
        
    def search(self, text):
        """
        search the database using text
        """
        # set the text in the entry even though in most cases the entry already
        # has the same text in it, this is in case this method was called from 
        # outside the class so the entry and search results match
        self.entry.set_text(text)
        self.current_search_text = text
        
        
        # clear the old model
        self.set_sensitive(False)
        bauble.app.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.results_view.set_model(None)        
        try:
            search = self.parse_text(text)
            self.populate_results(search)
        except SyntaxError, (msg, domain):
            model = gtk.ListStore(str)
            model.append(["Unknown search domain: " + domain])
            self.results_view.set_model(model)
        except ParseException, err:
            msg = 'Error in search string at column %s' % err.column
            model = gtk.ListStore(str)
            model.append([msg])
            self.results_view.set_model(model)
        except bauble.BaubleError, e:
            debug('BaubleError')
            debug(e)
            model = gtk.ListStore(str)
            model.append(['** Error: %s' % e])
            self.results_view.set_model(model)
        except:
            msg = "Could not complete search."
            utils.message_details_dialog(msg, traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)
        self.set_sensitive(True)
        bauble.app.gui.window.window.set_cursor(None)


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
        """
        look up the table type of the selected row and if it has
        any children then add them to the row
        """
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

    
    def query(self, domain, values):
        if domain == "default":
            results = []            
            for table_name in self.search_metas.keys():
                results += self.query_table(table_name, values)[:]
            return results
#        elif domain == 'sql':
#            debug(values[0])
#            conn = sqlobject.sqlhub.processConnection
#            sel = conn.queryAll(values[0])        
#            debug(sel)
#            return sel or ()
        elif not self.domain_map.has_key(domain):
            #raise KeyError('%s is not a recognized search domain' % domain)
            raise bauble.BaubleError('%s is not a recognized search domain' % \
                                     domain)
        else:
            table = self.domain_map[domain]
            return self.query_table(table, values)
        
                    
    def query_table(self, table_name, values):
#        debug(values)
        if table_name not in self.search_metas:
            raise ValueError("SearchView.query: no search meta for domain ", 
                              domain)
        search_meta = self.search_metas[table_name]
        table = search_meta.table
        columns = search_meta.columns
        
        # case insensitive searches
        # TODO: this should configurable in the preferences
        if sqlobject.sqlhub.processConnection.dbName == "postgres":
            like = "ILIKE"
        else:
            like = "LIKE"
            
        q = ''
        for v in values:
#            debug(v)
            if v == "*" or v == "all":
                s = table.select(orderBy=search_meta.sort_column)[:]
                return s
            if len(q) is 0:
                q = "%s %s '%%%s%%'" % (columns[0], like, v)
            else:
                q += " OR %s %s '%%%s%%'" % (columns[0], like, v)

            for c in columns[1:]:
                q += " OR %s %s '%%%s%%'" % (c, like, v)
#        debug(q)
        return table.select(q)
        
                
    # parser grammar definitions
#    __domain = Word(alphanums)
#    __quotes = Word('"' + "'")
#    __values_str = Word(alphanums+'*' +' '+';'+'.')    
#    __values = __quotes.suppress() + __values_str + __quotes.suppress() \
#               ^ __values_str
#    __expression = __domain + Word('=', max=2).suppress() + __values
    __domain = Word(alphanums)
    __quotes = Word('"' + "'")    
    __value_str = Word(alphanums+'*' +' '+';'+'.')
    __quoted_value_str = __quotes.suppress() + __value_str + __quotes.suppress()
    __value = __quoted_value_str ^ __value_str
    __single_value = __value
    __multiple_values = OneOrMore(__single_value + Word(',').suppress()) + \
                        Optional(__single_value)
    __possible_values = __single_value ^ __multiple_values
    __expression = __domain + Word('=', max=2).suppress() + __possible_values
    #__expression = __domain + Word('=') + __possible_values
                    
    parser = OneOrMore(Group(__expression ^ __possible_values))


    # FIXME: loc= search parses the search as ['default', 'loc'] instead
    # of a domain with an empty value list

    def parse_text(self, text):        
        parsed_string = self.parser.parseString(text)
        searches = {}        
        for group in parsed_string:
#            debug(group)            
#            if group[0].endswith('='):
#                raise bauble.BaubleError('no value given for domain: ' + \
#                                     group[0][:-1])
#            group[0] = group[0][:-1]
            
            if len(group) == 1:
                domain = 'default'
            elif group[0] in self.domain_map:
                domain = group[0]
                group = group[1:]
            else:
                domain = 'default'
            
            append = lambda v: searches[domain].append(v)
            try:
                map(append, group)
            except KeyError:
                searches[domain] = []
                map(append, group)
     
        return searches
        

    def populate_results(self, search):        
        bauble.app.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        #self.set_sensitive(False)	
        results = []
        added = False
        model = self.results_view.get_model()
        self.results_view.set_model(None) # temporarily remove the model

        if model is None: 
            model = gtk.TreeStore(object)
        
        for domain, values in search.iteritems():
            results += self.query(domain, values)
        
        if len(results) > 0:             
	    # don't bother sorting the results, if everything in the same
	    # level is of the same type then it probably has been sorted by
	    # the database any way and if it's not the same type then sorting
	    # a bunch of random types of data isn't that practical anyway
	    debug('appending results')
	    for r in results:                
		#model.append(model.append(None, [r]), '-')
		p = model.append(None, [r])

		# TODO: is it faster to check if it has children now or 
		# or just add the dummy row and check on expansion
                #print r.__class__.__name__
                #table_name = r.__class__.__name__
		#if table_name in self.view_meta and \
                #    self.view_meta[table_name].children is not None:
		model.append(p, ["-"])
        else: 
            model.append(None, ["Couldn't find anything"])


	debug('setting model')
        self.results_view.set_model(model)	
	debug('model set')
	bauble.app.gui.window.window.set_cursor(None)
    
    
    def append_children(self, model, parent, kids, have_kids):
        """
        append the elements of list <kids> to the model with parent <parent>
        if have_kids is true the string "_dummy" is appending to each
        of the kids kids
        @return the model with the kids appended
        """
        if parent is None:
            raise Exception("need a parent")
        for k in kids:
            i = model.append(parent, [k])
            if have_kids:
                model.append(i, ["_dummy"])
        return model
       
        
    def get_rowname(self, col, cell, model, iter):
        """
        return the string representation of some row inthe mode
        """
        # TODO:
        # it is possible that the row can be valid but the value returned
        # from __str__ is none b/c there is nothing in the column, this
        # really shouldn't b/c the column which we use for __str__
        # shouldn't have a default which means that somewhere it is
        # getting set 
        # explicitly to None, i think this is happening while importing one
        # of the geography tables with that funny empty row
        # UPDATE: the problem is with the name column of the Places table
        # it shouldn't have a default and in the fix_geo.py script we
        # should set the empty name to (cultivated) or something along
        # those lines
        row = model.get_value(iter, 0)
        if row is None:
            cell.set_property('text', "")
        elif isinstance(row, BaubleTable):
            cell.set_property('markup', row.markup())
        else:
            cell.set_property('text', str(row))
    

    def on_entry_key_press(self, widget, event, data=None):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.search_button.emit("clicked")
            
            
    def on_activate_editor(self, item, editor, select=None, defaults={}):
        e = editor(select=select, defaults=defaults)        
        committed = e.start()
        if committed is not None:
            self.refresh_search()        
#        response = e.start()
#        if response == gtk.RESPONSE_OK or response == gtk.RESPONSE_ACCEPT:        
#            e.commit_changes()
#            self.refresh_search()            
#        e.destroy()
        

    # TODO: provide a way for the plugin to add extra items to the
    # context menu of a particular type in the search results, this will
    # allow us to do things like have plugins customize the context menu
    #context_menu_items = []
    #def add_context_menu_item(self, obj_type, menu_item):
    #    pass
    
    def on_view_button_release(self, view, event, data=None):
        """
        popup a context menu on the selected row
        """
	# TODO: should probably fix this so you can right click on something
	# that is not the selection, but get the path from where the click
	# happened, make that that selection and then popup the menu,
	# see the pygtk FAQ about this at
	# http://www.async.com.br/faq/pygtk/index.py?req=show&file=faq13.017.htp
        if event.button != 3: 
            return # if not right click then leave
        sel = view.get_selection()
        model, i = sel.get_selected()
        if model == None:
            return # nothing to pop up a context menu on
        value = model.get_value(i, 0) 
        
        menu = gtk.Menu()

        editor_class = self.view_meta[value.__class__.__name__].editor
        if editor_class is not None:
            # value is a row in the table and .name is the name of the table
            # so find an editor with the same name as the table, this is a bit
            # basic and requires editors and tables to have the same name
            edit_item = gtk.MenuItem("Edit")
            # TODO: there should be a better way to get the editor b/c this
            # dictates that all editors are in ClassnameEditor format
    
            edit_item.connect("activate", self.on_activate_editor,
                              editor_class, [value], None)
            menu.add(edit_item)
            menu.add(gtk.SeparatorMenuItem())
        
        add_item = None
        for join in value.sqlmeta.joins:            
            # for each join in the selected row then add an item on the context
            # menu for adding rows to the database of the same type the join
            # points to
            defaults = {}            
            other_class = join.otherClassName
            if other_class in self.view_meta:
                editor_class = self.view_meta[other_class].editor # get editor 
                if join.joinColumn[-3:] == "_id": 
                    defaults[join.joinColumn.replace("_id", "ID")] = value
                    #defaults[join.joinColumn[:-3] + "ID"] = value        
                add_item = gtk.MenuItem("Add " + join.joinMethodName)                
                add_item.connect("activate", self.on_activate_editor, 
                                  editor_class, None, defaults)
                menu.add(add_item)
        
        if add_item is not None:
            menu.add(gtk.SeparatorMenuItem())
        
        remove_item = gtk.MenuItem("Remove")
        remove_item.connect("activate", self.on_activate_remove_item, value)
        menu.add(remove_item)
        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
        
        
    def on_activate_remove_item(self, item, row):
        # TODO: this will leave stray joins unless cascade is set to true
        # see col.cascade
        # TODO: should give a row specific message to the user, e.g if they
        # are removing an accession the accession number should be included
        # in the message as well as a list of all the clones associated 
        # with this accession
        row_str = '%s: %s' % (row.__class__.__name__, str(row))
        msg = "Are you sure you want to remove %s?" % row_str
        if utils.yes_no_dialog(msg):
            from sqlobject.main import SQLObjectIntegrityError
            try:
                row.destroySelf()
                # since we are doing everything in a transaction, commit it
                sqlobject.sqlhub.processConnection.commit() 
                self.refresh_search()
                
            except SQLObjectIntegrityError, e:
                msg = "Could not delete '%s'. It is probably because '%s' "\
                "still has children that refer to it.  See the Details for "\
                " more information." % (row_str, row_str)
                utils.message_details_dialog(msg, str(e))
            except:
                msg = "Could not delete '%s'. It is probably because '%s' "\
                "still has children that refer to it.  See the Details for "\
                " more information." % (row_str, row_str)
                utils.message_details_dialog(msg, traceback.format_exc())
    
    def on_view_row_activated(self, view, path, column, data=None):
        """
        expand the row on activation
        """
        view.expand_row(path, False)
            

    def create_gui(self):
        """
        create the interface
        """
        self.content_box = gtk.VBox()  
                  
        # create the entry and search button
        self.entry = gtk.Entry()
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
        
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Name", renderer)
        
        column.set_cell_data_func(renderer, self.get_rowname)
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
        

    def on_activate_gbif_expand(self, expander, data=None):
        """
        """
        expanded = expander.get_expanded()
        gbif = expander.get_child()
        # this is fired before the expanded state is set so we should assume
        # that if this is fired the opposite is being done. e.g. if it is 
        # activate and is currently expanded we should assume it us being
        # collapsed
        if not expanded and gbif is None:
            gbif = views.views.GBIFView(bauble)
            expander.add(gbif)
        elif gbif is not None:
            expander.remove(gbif)
            
        
    # TODO: should i or should i not delete everything that is a child
    # of the row when it is collapsed, this would save memory but
    # would cause it to be slow if rows were collapsed and need to be
    # reopend
    def on_row_collapsed(self, view, iter, path, data=None):
        """        
        """
        pass
       

