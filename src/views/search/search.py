#
# search.py
#

import re, threading
import gtk
import sqlobject
import views
from tables import tables
from editors import editors
from utils.debug import debug
import utils

debug.enable = True

from bauble import bauble

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

class SearchView(views.View):
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
    search_map = { "Families": [tables.Families, ("family",)],
                   "Genera":   [tables.Genera, ("genus",)],
                   "Plantnames": [tables.Plantnames, ("sp","isp")],
                   'Accessions': [tables.Accessions, ("acc_id",)],
                   'Locations': [tables.Locations, ("site",)]}
                   
    # other domain to implement  
    # name, sp, species (shouldn't use "name", implies full name)
    # native, origin
    # loc, location
    # edible,
    # medicine
    # redlist, conservation
    domain_map = {'Families': ('family', 'fam'),
                      'Genera': ('genus', 'gen'),
                      'Plantnames': ('species', 'sp'),
                      'Accessions': ('accession', 'acc'),
                      'Locations': ('location', 'loc')}
    child_expand_map = {tables.Families: 'genus',
                        tables.Genera: 'plantnames',
                        tables.Plantnames: 'accessions',
                        tables.Accessions: 'plants',
                        tables.Locations: 'plants'}


    def __init__(self):
        views.View.__init__(self)
        self.create_gui()
        self.entry.grab_focus()


    def on_results_view_select_row(self, view):
        """
        add and removes the info_box which should change depending on
        the type of the row selected
        """        
        sel = view.get_selection() # get the selected row
        model, i = sel.get_selected()
        value = model.get_value(i, 0)
        
        if self.info_box is not None:
            if self.info_box.parent == self.pane:
                self.pane.remove(self.info_box) # remove the old info
            self.info_box.destroy() # does thi s cause it to be garbage collected
            
        if type(value) == tables.Plants:
            self.info_box = PlantsInfoBox()
            self.info_box.get_expander("Locations").set_values(value.location)
            self.pane.pack2(self.info_box, True, False)

        #self.info_box = None
        self.pane.show_all()
        
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
        expand = False
        model = view.get_model()
        row = model.get_value(iter, 0)
        view.collapse_row(path)
        self.remove_children(model, iter)
        t = type(row)
        bauble.gui.pulse_progressbar()
        for table, child in self.child_expand_map.iteritems():
            if t == table:
                kids = getattr(row, child)
                if len(kids):
                    self.append_children(model, iter, kids, True)
                    bauble.gui.stop_progressbar()
                    return False
        bauble.gui.stop_progressbar()
        return True

        
    def query(self, domain, values):
        """
        """
        if domain == "default": # search all field in search_map
            results = []
            for d in self.search_map.keys():
                results += self.query(d, values)
            return results
        
        table = self.search_map[domain][0]
        fields = self.search_map[domain][1]
        for v in values:
            if v == "*" or v =="all": return table.select()
            q = "%s LIKE '%%%s%%'" % (fields[0], v)
            for f in fields[1:]:
                q += " OR %s LIKE '%%%s%%'" % (f, v)
        return table.select(q)
                

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
        bauble.gui.stop_progressbar()


    def populate_results(self, search):        
        #import pdb
        self.CANCEL = False
        self.set_sensitive(False)
        bauble.gui.pulse_progressbar()
        thread = threading.Thread(target=self.populate_worker, args=(search,))
        thread.start()
        
    
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
        if row is None:
            cell.set_property('text', "")
        else: cell.set_property('text', str(row))


    def on_key_press(self, widget, event, data=None):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            self.execute_button.emit("clicked")
            
            
    def on_activate_editor(self, item, editor, select=None, defaults={}):
        e = editor(select=select, defaults=defaults)
        e.show()

        
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
        edit_item.connect("activate", self.on_activate_editor,
                          eval("editors.%s" % value.name), [value], None)
        menu.add(edit_item)
         
        menu.add(gtk.SeparatorMenuItem())
        
        for join in value._joins:
            # for each join in the selected row then add an item on the context
            # menu for adding rows to the database of the same type the join
            # points to
            # TODO: this is a pretty wretched hack looking up from the kw 
            # attribute of the join columns, but it works
            defaults = {}
            name = join._joinMethodName 
            join_column = join.kw["joinColumn"]
            # if join column not in the format "column_id" then don't do anything
            if join_column[-3:] == "_id": 
                defaults[join_column[:-3]] = value
            
            other_class = join.kw["otherClass"]
            add_item = gtk.MenuItem("Add " + name)
            add_item.connect("activate", self.on_activate_editor, 
                         eval("editors.%s" % other_class), None, 
                         defaults)
            menu.add(add_item)
        
        menu.add(gtk.SeparatorMenuItem())
        
        remove_item = gtk.MenuItem("Remove")
        remove_item.connect("activate", self.on_activate_remove_item, value)
        menu.add(remove_item)
        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
        return
        
        
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
        # TODO: this should immediately remove the model from the value
        # and refresh the tree, we might have to save the path to
        # remember where we were in the view

        
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
        sw.add(self.results_view)

        # the info box
        #self.info_box = InfoBox() # empty InfoBox
        self.info_box = None
        
        # pane to split the results view and info_box
        self.pane = gtk.HPaned()
        self.pane.pack1(sw, True, False)
        #self.pane.pack2(self.info_box, True, False)
        pane_box = gtk.HBox(False)
        pane_box.pack_start(self.pane, True, True)
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
        
        self.content_box.pack_start(pane_box)
        
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
       

class InfoExpander(gtk.Expander):
    """
    a generic expander with a vbox
    """
    # TODO: we should be able to make this alot more generic
    # and get information from sources other than table columns
    
    def __init__(self, label):
        gtk.Expander.__init__(self, label)
        self.vbox = gtk.VBox(False)
        self.add(self.vbox)


class TableExpander(InfoExpander): 
    """
    an InfoExpander to represent columns in a table
    """
    
    def __init__(self, label, columns):
        """
        columns is a dictionary of {column: name}
        """
        InfoExpander.__init__(self, label)
        self.labels = {}
        for column, name in columns.iteritems():
            label = gtk.Label()
            label.set_alignment(0.0, 0.5)
            self.vbox.pack_start(label, False, False)
            self.labels[column] = (name, label)
        
    
    def set_values(self, values):
        """
        populate the labels according to the values in result, should
        only be a single row
        """
        for col in self.labels.keys():
            value = eval("str(values.%s)" % col)
            name, label = self.labels[col] 
            label.set_text("%s: %s" % (name, value))
            

class LocationsExpander(TableExpander):
    """
    TableExpander for the Locations table
    """
    
    def __init__(self, label="Locations", columns={"site": "Site"}):
        TableExpander.__init__(self, label, columns)


class InfoBoxFactory:
    def createInfoBox(type):
        pass

        
class InfoBox(gtk.VBox):
    """
    a VBox with a bunch of InfoExpanders
    """
    
    def __init__(self):
        gtk.VBox.__init__(self, False)
        self.expanders = {}
        
    def add_expander(self, expander):
        self.pack_start(expander, False, False)
        self.expanders[expander.get_property("label")] = expander
    
    def get_expander(self, label):
        if self.expanders.has_key(label): 
            return self.expanders[label]
        else: return None
    
    def remove_expander(self, label):
        if self.expanders.has_key(label): 
            self.remove(self.expanders[label])
        
            
class PlantsInfoBox(InfoBox):
    """
    an InfoBox for a Plants table row
    """
    def __init__(self):
        InfoBox.__init__(self)
        loc = LocationsExpander()
        loc.set_expanded(True)
        self.add_expander(loc)