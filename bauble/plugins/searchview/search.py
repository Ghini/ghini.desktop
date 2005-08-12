#
# search.py
#

import re, threading
import gtk
import sqlobject
#import views
#from tables import tables
#from editors import editors
from utils.debug import debug
import utils
import infobox

debug.enable = True
from bauble.plugins import plugins
tables = plugins.tables

import bauble
#from bauble import bauble

# NOTE: to add a new search domain do:
# 1. add table to search map with columns to search
# 2. add domain keys to domain map
# 3. if you want a result to expand on one of its children then
#    add the table and the default child to child_expand_map

# TODO: whenever an editor is called and changes are commited we should get 
# a list of expanded paths and then search again on the same criteria and then
# reexpand the paths that were saved and the path of the item that was the editor
# was called on

# TODO: things todo when a result is selected
# - GBIF search results, probably have to look up specific institutions
# - search Lifemapper for distributions maps
# - give list of references and images and make then clickable if they are uris

# TODO: could push the search map into the table modules so each table can
# have its own search map thens this module doesn't have to know about all the 
# tables, it only has to query the tables module for the search map for all 
# tables, could also do something similar to domain map and child expand
# map


#class SearchView(views.View):
    
from bauble.plugins import BaubleView
    

class SearchView(BaubleView):
    """
    1. all search parameters are by default ANDed together unless two of the
    same class are give and then they are ORed, e.g. fam=... fam=... will
    give everything that matches either one\
    2. should follow some sort of precedence using AND, OR and parentheses
    3. if the search get too complicated we may have to define a language
    4. search specifically by family, genus, sp, isp(x?), author,
    garden location, country/region or origin, conservation status, edible
    5. possibly add families/family=Arecaceae, Orchidaceae, Poaceae
    """    
    search_map = {"Family": [tables.Family, ("family",)],
                  "Genus":   [tables.Genus, ("genus",)],
                  "Plantname": [tables.Plantname, ("sp","isp")],
#                  'Accessions': [tables.Accessions, ("acc_id",)],
#                  'Locations': [tables.Locations, ("site",)],
#                  'Continents': [tables.Continents, ('continent',)],
#                  'Regions': [tables.Regions, ('region',)],
#                  'Areas': [tables.Areas, ("area",)],
#                  'States': [tables.States, ('state',)],
#                  'Places': [tables.Places, ('name',)],
#                  'KewRegions': [tables.KewRegions, ('region',)]
                  }
                   
    # other domain to implement  
    # name, sp, species (shouldn't use "name", implies full name)
    # native, origin
    # loc, location
    # edible,
    # medicine
    # redlist, conservation
    # the keys here point to the esarch map, not a necessarily a table
    domain_map = {'Family': ('family', 'fam'),
                  'Genus': ('genus', 'gen'),
                  'Plantname': ('species', 'sp'),
#                  'Accessions': ('accession', 'acc'),
#                  'Locations': ('location', 'loc'),
#                  'Continents': ('continent',),
#                  'Regions': ('region',),
#                  'Areas': ('area',),
#                  'States': ('state',),
#                  'Places': ('place',),
#                  'KewRegions': ('kewregion',),
                  }
                  
    # TODO: check child expand map before adding _dummy
    child_expand_map = {tables.Family: 'genus',
                        tables.Genus: 'plantnames',
                        tables.Plantname: 'accessions',
#                        tables.Accessions: 'plants',
#                        tables.Locations: 'plants'
                        }
                        
    infobox_map = {tables.Plantname: infobox.PlantnamesInfoBox,
#                   tables.Plant: infobox.PlantsInfoBox,
#                   tables.Accessions: infobox.AccessionsInfoBox
                   }
                 
    
    def __init__(self):
        #views.View.__init__(self)
        super(SearchView, self).__init__()
        self.create_gui()
        self.entry.grab_focus() # this doesn't seem to work

    
    def set_infobox_from_row(self, row):
        #return
        if not hasattr(self, 'infobox'):
            self.infobox = None
            
        if self.infobox is not None:
            if self.infobox.parent == self.pane:
                self.pane.remove(self.infobox)
            self.infobox.destroy()
            
        t = type(row)
        #if self.infobox_map.has_key(t):
        if t in self.infobox_map:
            self.infobox = self.infobox_map[t]()
            if row is not None:
                self.infobox.update(row)
            self.pane.pack2(self.infobox, False, True)
            #self.pane.pack2(self.infobox, True, True)
        self.pane.show_all() # reset the pane

        
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
        

    def on_pb_cancel(self, response, data=None):
        if response == gtk.RESPONSE_CANCEL:
            self.CANCEL = True

    
    def on_execute_clicked(self, widget):
        text = self.entry.get_text()
        self.current_search_text = text
        self.search(text)
        
        
    current_search_text = None
    
    def search(self, text):
        """
        search the database using text
        """
        # clear the old model
        self.results_view.set_model(None)
        
        try:
            search = self.parse_text(text)
        except Exception, (msg, domain):
            model = gtk.ListStore(str)
            model.append(["Unknown search domain: " + domain])
            self.results_view.set_model(model)
            return
                
        self.populate_results(search)


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
        print 'entered SearchView.on_text_expand_row()'
        expand = False
        model = view.get_model()
        row = model.get_value(iter, 0)
        view.collapse_row(path)
        self.remove_children(model, iter)
        t = type(row)
        #bauble.gui.pulse_progressbar()
        for table, child in self.child_expand_map.iteritems():
            if t == table:
                kids = getattr(row, child)
                if len(kids):
                    self.append_children(model, iter, kids, True)
                    #bauble.gui.stop_progressbar()
                    print 'leaving SearchView.on_text_expand_row(): False'
                    return False
        #bauble.gui.stop_progressbar()
        print 'leaving SearchView.on_text_expand_row(): True'
        return True

        
    def query(self, domain, values):
        """
        """
        if domain == "default": # search all field in search_map
            results = []
            for d in self.search_map.keys():
                results += self.query(d, values)
            return results
        
        if domain not in self.search_map or self.search_map[domain] is None:
            raise ValueError("SearchView.query(): the domain %s is not in "\
                             "the search map or is None" % d)
        
        
        table = self.search_map[domain][0]
        if table is None:
            raise ValueError("SearchView.query(): the table registered "\
                             "for the domain %s is not valid" % domain)
        fields = self.search_map[domain][1]
        
        for v in values:
            if v == "*" or v =="all": 
                #return table.select()
                return table.select(connection=bauble.app.conn)
            q = "%s LIKE '%%%s%%'" % (fields[0], v)
            for f in fields[1:]:
                q += " OR %s LIKE '%%%s%%'" % (f, v)
        return table.select(q, connection=bauble.app.conn)
        #return table.select(q)
                

    def parse_text(self, text):
        """
        """
        # TODO: should allow plurals like genera=1,2 and parse
        # them apart, also need to account for values in quotations        
        pieces = text.split(' ')
        #rx = re.compile("\s*\S+={1,2}\S+\s*")
        rx = re.compile("(\S+)={1,2}(\S+)")
        searches = {}
        for p in pieces:
            m = rx.match(p)
            if m is None:
                if "default" not in searches: searches["default"] = []
                searches["default"].append(p)
            else:                
                g = m.groups()                
                domain = self.resolve_domain(g[0])
                if domain not in self.search_map:
                    raise Exception("views.search: unknown search domain: " + g[0], g[0])
                if domain not in searches: searches[domain] = []
                searches[domain].append(g[1])
        return searches


    def resolve_domain(self, domain):
        """
        given some string this method returns a table name or None if the
        string doesn't match a table
        """
        for key, values in self.domain_map.iteritems():
            if domain.lower() in values:
                return key
        return None

    
    def populate_worker(self, search):
        gtk.gdk.threads_enter()
        results = []
        added = False
        model = self.results_view.get_model()
        self.results_view.set_model(None) # temporary
        if model is None: 
            model = gtk.TreeStore(object)
        for domain, values in search.iteritems():
            results += self.query(domain, values)
            for r in results:
                added = True
                p = model.append(None, [r])
                model.append(p, ["_dummy"])
        if not added:
            model.append(None, ["Couldn't find anything"])
        self.results_view.set_model(model)
        self.set_sensitive(True)
        gtk.gdk.threads_leave()
        #bauble.gui.stop_progressbar()


    def populate_results(self, search):        
        self.CANCEL = False
        self.set_sensitive(False)
        #bauble.gui.pulse_progressbar()
        #thread = threading.Thread(target=self.populate_worker, args=(search,))
        #thread.start()
        # there's really no point setting the cursor for a long operation
        # without threading b/c the cursor doesn't get updated, maybe if 
        # waited for half second or so
        import gtk.gdk
        bauble.app.gui.window.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.populate_results_no_threading(search)
        bauble.app.gui.window.window.set_cursor(None)
        
        
    def populate_results_no_threading(self, search):
        self.set_sensitive(False)
        results = []
        added = False
        model = self.results_view.get_model()
        self.results_view.set_model(None) # temporary
        if model is None: 
            model = gtk.TreeStore(object)
        
        for domain, values in search.iteritems():
            results += self.query(domain, values)
        
        if len(results) > 0: 
            for r in sorted(results, cmp=lambda x, y: cmp(str(x), str(y))):
                p = model.append(None, [r])
                model.append(p, ["_dummy"])
        else: 
            model.append(None, ["Couldn't find anything"])
        
        self.results_view.set_model(model)
        self.set_sensitive(True)
    
    
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
        row = model.get_value(iter, 0)
        #print row
        if row is None:
            cell.set_property('text', "")
        else:
            # TODO:
            # it is possible that the row can be valid but the value returned
            # from __str__ is none b/c there is nothing in the column, this
            # really shouldn't b/c the column which we use for __str__ shouldn't
            # have a default which means that somewhere it is getting set 
            # explicitly to None, i think this is happening while importing one
            # of the geography tables with that funny empty row
            # UPDATE: the problem is with the name column of the Places table
            # it shouldn't have a default and in the fix_geo.py script we should
            # set the empty name to (cultivated) or something along those lines
            cell.set_property('text', str(row))


    def on_key_press(self, widget, event, data=None):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.execute_button.emit("clicked")
            
            
    def on_activate_editor(self, item, editor, select=None, defaults={}):
        print 'entered SearchView.on_activate_editor()'
        e = editor(select=select, defaults=defaults)
        e.start()
        print 'SearchView.on_activate_editor: started'
        #e.show()

        
    def on_view_button_release(self, view, event, data=None):
        """
        popup a context menu on the selected row
        """
        if event.button != 3: return # if not right click then leave
        sel = view.get_selection()
        model, i = sel.get_selected()
        value = model.get_value(i, 0) 
        
        menu = gtk.Menu()
        # value is a row in the table and .name is the name of the table
        # so find an editor with the same name as the table, this is a bit
        # basic and requires editors and tables to have the same name
        edit_item = gtk.MenuItem("Edit")
        # TODO: there should be a better way to get the editor b/c this
        # dictates that all editors are in ClassnameEditor format
        edit_item.connect("activate", self.on_activate_editor,
                          editors[value.__class__], [value], None)
        menu.add(edit_item)
        menu.add(gtk.SeparatorMenuItem())
        
        for join in value.sqlmeta.joins:
            # for each join in the selected row then add an item on the context
            # menu for adding rows to the database of the same type the join
            # points to
            # TODO: this is a pretty wretched hack looking up from the kw 
            # attribute of the join columns, but it works
            defaults = {}
            
            # if join column not in the format "column_id" then don't do anything
            # 
            # *** i don't understand this comment
            #
            if join.joinColumn[-3:] == "_id": 
                defaults[join.joinColumn[:-3]] = value
            
            if join.otherClassName in editors:          
                add_item = gtk.MenuItem("Add " + join.joinMethodName)                
                add_item.connect("activate", self.on_activate_editor, 
                                  editors[join.otherClassName], None, defaults)
                                 #editors[editor_name], None, defaults)
                menu.add(add_item)
        
        menu.add(gtk.SeparatorMenuItem())
        
        remove_item = gtk.MenuItem("Remove")
        remove_item.connect("activate", self.on_activate_remove_item, value)
        menu.add(remove_item)
        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
        
        
    def on_activate_remove_item(self, item, row):
        print "removing " + str(row)
        # TODO: this will leave stray joins unless cascade is set to true
        # see col.cascade
        # TODO: should give a row specific message to the user, e.g if they
        # are removing an accession the accession number should be included
        # in the message as well as a list of all the clones associated 
        # with this accession
        msg = "Are you sure you want to remove this?"
        if utils.yes_no_dialog(msg):
            row.destroySelf()
        
        self.search(self.current_search_text)
        # TODO: this should immediately remove the model from the value
        # and refresh the tree, we might have to save the path to
        # remember where we were in the view
        # TODO: we can probably just accomplish this by collapsing and then
        # expanding the parent of the item to be removed

        
    def on_view_row_activated(self, view, path, column, data=None):
        """
        expand the row on activation
        """
        view.expand_row(path, False)
            

    def create_gui(self):
        """
        create the interface
        """
        self.content_box = gtk.VBox(False)  
              
        # create the entry and search button
        self.entry = gtk.Entry()
        self.entry.connect("key_press_event", self.on_key_press)
        self.execute_button = gtk.Button("Search")
        self.execute_button.connect("clicked", self.on_execute_clicked)
        
        entry_box = gtk.HBox(False) # hold the search entry and execute_button
        entry_box.pack_start(self.entry, True, True)        
        entry_box.pack_end(self.execute_button, False, False)
        self.content_box.pack_start(entry_box, False, False)
        
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
        self.show_all()
        

    def on_activate_gbif_expand(self, expander, data=None):
        """
        """
        print "SearchView.on_activate_gbif_expand()"
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
       

