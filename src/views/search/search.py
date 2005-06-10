#
# search.py
#

import re
import pygtk
pygtk.require("2.0")
import gtk
import sqlobject
import views
from tables import tables
from editors import editors
import gtasklet

from utils.debug import debug
debug.enable = True

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
                   "Plantnames": [tables.Plantnames, ("sp","isp")]
                   }

    __name__ = "SearchView"


    def __init__(self, bauble):
        views.View.__init__(self)
        self.bauble = bauble
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
            self.pane.remove(self.info_box) # remove the old info
            self.info_box.destroy() # does this cause it to be garbage collected
            
        if type(value) == tables.Plants:
            self.info_box = PlantsInfoBox()
            self.info_box.get_expander("Locations").set_values(value.location)
            self.pane.pack2(self.info_box, True, True)

        self.info_box = None
        #self.pane.show_all()
        
        # check that the gbif view is expanded
        # if it is then pass the selected row to gbif
        if self.gbif_expand.get_expanded():
            gbif = self.gbif_expand.get_child()
            gbif.search(value)
        

    def on_pb_cancel(self, response, data=None):
        if response == gtk.RESPONSE_CANCEL:
            self.CANCEL = True

            
    def on_execute_clicked(self, widget):
        text = self.entry.get_text()
        search = self.parse_text(text)
                
        # clear the old model
        self.results_view.set_model(None)
        self.populate_results(search)

        
    def populate_task(self, tasklet, search):
        results = []
        timeout = gtasklet.WaitForTimeout(10)
        added = False
        for domain, values in search.iteritems():
            yield timeout
            results += self.query(domain, values)
            if self.CANCEL: break
            for r in results:
                added = True
                p = self.append_result(r)
                self.append_result("_dummy", p)
                if self.CANCEL: break
            if self.CANCEL: break

        if self.CANCEL: 
            self.results_view.set_model(None) # incomplete, clear model

        if not added:
            self.append_result("Couldn't find anything")

        self.bauble.gui.stop_progressbar()


    def populate_results(self, search):        
        #import pdb
        self.CANCEL = False
        
        self.bauble.gui.pulse_progressbar()
        gtasklet.Tasklet(self.populate_task, search)
        #pb = self.bauble.gui.progressbar
        #
        #thread.start_new_thread(self.populate_worker, (search,))
        #pdb.set_trace()
        

    def populate_results1(self, search):
        debug("enter populate")
        self.CANCEL = False
        #pb = self.bauble.gui.progressbar
        self.bauble.gui.pulse_progressbar()
        
        results = []
        for domain, values in search.iteritems():            
            results += self.query(domain, values)
            if self.CANCEL: break
            for r in results:
                #pb.pulse()
                p = self.append_result(r)
                self.append_result("_dummy", p)
                if self.CANCEL: break
            if self.CANCEL: break

        if self.CANCEL: 
            self.results_view.set_model(None) # incomplete, clear model
            
        self.bauble.gui.stop_progressbar()            
        #pb.destroy()
        

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
        """
        expand = False
        model = view.get_model()
        row = model.get_value(iter, 0)
        view.collapse_row(path)
        self.remove_children(model, iter)
        t = type(row)
        # TODO: should be able to set in the meta of the table
        if t == tables.Families and len(row.genus) > 0:
            self.append_children(iter, row.genus, True)
        elif t == tables.Genera and len(row.plantnames) > 0:
            self.append_children(iter, row.plantnames, True)
        elif t == tables.Plantnames and len(row.accessions) > 0:
            self.append_children(iter, row.accessions, True)
        elif t == tables.Accessions and len(row.plants) > 0:
            self.append_children(iter, row.plants, True)
        else: expand = True
        return expand

        
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
            q = "%s  LIKE '%%%s%%'" % (fields[0], v)
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
                if domain not in searches: searches[domain] = []
                searches[domain].append(g[1])
        return searches


    def resolve_domain(self, domain):
        #
        # TODO: could put each of these matches in a dictionary and if it
        # matches the dict value then the key becomes the domain
        #
        if re.match("(family)|(fam)", domain, re.I) is not None:
            return "Families"
        elif re.match("(genus)|(gen)", domain, re.I) is not None:
            return "Genera"
        elif re.match("(species)|(sp)", domain, re.I) is not None:
            return "Plantnames"
        elif re.match("(accession)|(acc)", domain, re.I) is not None:
            return "Accessions"        
        # if fam, family
        # if gen, genus
        # name, sp, species (shouldn't use "name", implies full name)
        # if acc, accession
        # native, origin
        # loc, location
        # edible,
        # medicine
        # redlist, conservation
        

    def append_children(self, iter, kids, have_kids):
        """
        add children to row pointed to by iter
        have_hids = if the kids have kids
        """
        if iter is None:
            raise Exception("need a parent")
        self.bauble.gui.pulse_progressbar()
        gtasklet.Tasklet(self.append_children_task, kids, iter, have_kids)
        
        
    def append_children_task(self, task, kids, iter, have_kids):
        timeout = gtasklet.WaitForTimeout(1)
        for k in kids:
            #
            i = self.append_result(k, iter)            
            if have_kids:                
                self.append_result("_dummy", i)
            # TODO: if i yield in this loop then i get invalid iters
            # yield timeout 
        self.bauble.gui.stop_progressbar()
        #gtk.gdk.flush()
        
        
    def append_result(self, row, parent=None):
        """
        returns TreeIter pointing to row added,
        i don't think this function is really necessary, could
        probably put the same thing in on_execute_clicked
        """
        model = self.results_view.get_model()        
        if model is None:
            model = gtk.TreeStore(object)
            self.results_view.set_model(model)            
        return model.append(parent, [row])
                                        
        
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
        
        
        edit_item = gtk.MenuItem("Edit")
        edit_item.connect("activate", self.on_activate_editor,
                          eval("editors.%s" % value.name), [value], None)
        menu.add(edit_item)
         
        # TODO: add a separator
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
        
        
        menu.show_all()
        menu.popup(None, None, None, event.button, event.time)
        return
        
        
        

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
        self.info_box = InfoBox() # empty InfoBox
        
        # pane to split the results view and info_box
        self.pane = gtk.HPaned()
        self.pane.pack1(sw, True, True)
        self.pane.pack2(self.info_box, True, False)
        pane_box = gtk.HBox(False)
        pane_box.pack_start(self.pane, True, True)
        #self.content_box.pack_start(self.pane, True, True)
        
        # add the GBIFView 
        # create the expander but don't create the GBIFView object unless
        # it's expanded, should later remove the view or at least disable
        # it if the expander is collapsed
        
        self.gbif_expand = gtk.Expander("Online Search")
        self.gbif_expand.connect("activate", self.on_activate_gbif_expand)
        # if starting expanded then we have to create the gbif view b/c 
        # the activate signal is not throws
        #gbif = views.views.GBIFView(self.bauble)
        #self.gbif_expand.add(gbif)
        self.gbif_expand.set_expanded(False)
        vpane = gtk.VPaned()
        vpane.pack1(pane_box, True, True)
        vpane.pack2(self.gbif_expand, True, True)
        self.content_box.pack_start(vpane, True, True)
        
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
            gbif = views.views.GBIFView(self.bauble)
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
            label.set_justify(gtk.JUSTIFY_LEFT)
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