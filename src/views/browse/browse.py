#
# browse.py
#

import re
import gtk
import views
from tables import tables

# TODO: remove gtasklet stuff
#import gtasklet

class SQLListStore(gtk.ListStore):
    """
    each row in the list store is a row from the sqlobject.Select
    TODO: is it possible to do a lazy add to the model so that the row
    is only requested from the select when it the value is gotten from
    the store
    """
    def __init__(self, select):
        gtk.ListStore.__init__(self, object)
        for row in select:
            self.append([row])     


#
# InfoExpander
#
class InfoExpander(gtk.Expander):
    #_labels = {}

    
    def __init__(self, label, dict):
        gtk.Expander.__init__(self, label)
        NONE = 0
        expand = gtk.Expander(label)
        table = gtk.Table(len(dict), 2)
        row = 0
        self._labels = {}
        #keys = dict.keys() # keep them in order,        
        #keys.reverse()     # though not guaranteed between instantiations
        for key in dict.keys():            
            lab = gtk.Label(dict[key])
            lab.set_alignment(1, .5) # doesn't seem to work
            table.attach(lab, 0, 1, row, row+1, NONE, NONE)
            self._labels[key] = gtk.Label("")
            self._labels[key].set_alignment(1, .5)
            table.attach(self._labels[key], 1, 2, row, row+1, NONE, NONE)
            row = row+1
        self.add(table)
        #self.set_expanded(True)

        
    def set_label(self, name, value):
            self._labels[name].set_text(value)

#
# BrowseFrame
#
class BrowseView(views.View):
    
    def __init__(self, bauble):
        #gtk.Frame.__init__(self,label="")
        views.View.__init__(self)
        self.bauble = bauble
        self.plants_box = None
        self.acc_view = None # add this dynamically
        self.create_gui()
        

    # 
    # cell renderer data fuctions
    #
    def get_fam(self, col, cell, model, iter):
        row = model.get_value(iter, 0)        
        cell.set_property('text', row.family)

    
    def get_gen(self, col, cell, model, iter):
        row = model.get_value(iter, 0)        
        cell.set_property('text', row.genus)


    def get_name(self, col, cell, model, iter):
        row = model.get_value(iter, 0)
        import plant
        p = plant.Plant(row.genus.genus, species=row.sp, isp_rank=row.isp_rank,
                        isp=row.isp)
        cell.set_property('text', str(p))


    def get_acc(self, col, cell, model, iter):
        row = mode.get_value(iter, 0)
        cel.set_property('text', row.acc_id)

    #
    # row selected functions
    #
    def on_name_view_select_row(self, widget):
        """ populate self.acc_view with names that match the selected genus"""
        # select all accessions with this name
        sel = widget.get_selection()
        name_model, i = sel.get_selected()
        row = name_model.get_value(i, 0)
        model = SQLListStore(row.accessions)

        if self.acc_view is None:            
            self.plants_box.pack_start(self.create_acc_view())
            self.plants_box.show_all() # otherwise you can't see it
        self.acc_view.set_model(model)


    def on_gen_view_select_row(self, widget):
        """ populate self.name_view with names that match the selected genus"""
        sel = widget.get_selection()
        gen_model, i = sel.get_selected()
        row = gen_model.get_value(i, 0)
        model = SQLListStore(row.plantnames)
        self.name_view.set_model(model)

    
    def on_fam_view_select_row(self, widget):
        """ populate self.gen_view with names that match the selected genus"""
        sel = widget.get_selection()
        fam_model, i = sel.get_selected()

        row = fam_model.get_value(i, 0)
        self.gen_label_str = "Genera"
        self.gen_label.set_text("%s (%i in %s)" %
                                (self.gen_label_str,len(row.genus), row))
        model = SQLListStore(row.genus)
        self.gen_view.set_model(model)

        # should also change the info_expanders values
        # if it is expanded
        if not self.fam_info.get_expanded():
            return
        self.fam_info.set_label("id", str(row.id))
        #self.fam_info.set_label("comments", row. Comments)


    def on_acc_view_select_row(self, widget):
        pass

    #
    # interface creation functions
    #
    def populate_gui(self, pb, dialog):
        vbox = gtk.VBox(False)
        vbox.set_spacing(5)
        pb.pulse()        
        vbox.pack_start(self.create_fam_frame())
        pb.pulse()
        vbox.pack_start(self.create_gen_frame())        
        pb.pulse()
        hbox = gtk.HBox(False)
        hbox.set_spacing(5)
        hbox.pack_start(vbox)

        self.plants_box = gtk.VBox(False)
        self.plants_box.pack_start(self.create_name_frame())
        hbox.pack_start(self.plants_box)
        self.add(hbox)
        dialog.destroy()
        self.show_all()

        
    def create_gui(self):
        dialog = gtk.Dialog(title="Loading...", parent=None,
                            buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL))
        pb = gtk.ProgressBar()
        dialog.vbox.pack_start(pb)
        #dialog.show_all()
        #import thread
        #thread.start_new_thread(self.populate_gui, (pb, dialog))
        self.populate_gui(pb, dialog)
        #dialog.run()


    def create_acc_view(self):
        vbox = gtk.VBox(False)

        label = gtk.Label("Accessions")
        new_button = gtk.Button("New")
        edit_button = gtk.Button("Edit")
        box = gtk.HBox(False)
        box.pack_start(label, fill=False, expand=False)        
        box.pack_end(edit_button, fill=False, expand=False)
        box.pack_end(new_button, fill=False, expand=False)
        vbox.pack_start(box, fill=False, expand=False)

        new_button.connect("clicked", self.on_new_acc_clicked)
        edit_button.connect("clicked", self.on_edit_acc_clicked)
        
        self.acc_view = gtk.TreeView()
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Accession", renderer)
        column.set_cell_data_func(renderer, self.get_acc)
        self.acc_view.append_column(column)
        self.acc_view.set_headers_visible(False)

        # signal handler
        self.name_view.connect("cursor-changed", self.on_acc_view_select_row)
        
        sw = gtk.ScrolledWindow()
        sw.add(self.acc_view)
        #frame_box.pack_start(sw)
        vbox.pack_start(sw)
        return vbox


    def create_name_frame(self):
        frame_box = gtk.VBox(False)
        
        label = gtk.Label("Names")
        new_button = gtk.Button("New")
        edit_button = gtk.Button("Edit")
        box = gtk.HBox(False)
        box.pack_start(label, fill=False, expand=False)        
        box.pack_end(edit_button, fill=False, expand=False)
        box.pack_end(new_button, fill=False, expand=False)
        frame_box.pack_start(box, fill=False, expand=False)

        new_button.connect("clicked", self.on_new_name_clicked)
        edit_button.connect("clicked", self.on_edit_name_clicked)

        self.name_view = gtk.TreeView()
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Species", renderer)
        column.set_cell_data_func(renderer, self.get_name)
        self.name_view.append_column(column)
        self.name_view.set_headers_visible(False)

        # signal handlers
        self.name_view.connect("cursor-changed", self.on_name_view_select_row)
        
        sw = gtk.ScrolledWindow()
        sw.add(self.name_view)
        frame_box.pack_start(sw)
        return frame_box

    
    def create_fam_frame(self):
        frame_box = gtk.VBox(False)

        label = gtk.Label("Families (%i)" % tables.Families.select().count())
        new_button = gtk.Button("New")
        edit_button = gtk.Button("Edit")
        box = gtk.HBox(False, 3)
        box.pack_start(label, fill=False, expand=False)        
        box.pack_end(edit_button, fill=False, expand=False)
        box.pack_end(new_button, fill=False, expand=False)
        frame_box.pack_start(box, fill=False, expand=False)

        new_button.connect("clicked", self.on_new_fam_clicked)
        edit_button.connect("clicked", self.on_edit_fam_clicked)
        
        family_model = SQLListStore(tables.Families.select())            
        self.fam_view = gtk.TreeView(family_model)
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Family", renderer)
        column.set_cell_data_func(renderer, self.get_fam)
        self.fam_view.append_column(column)
        self.fam_view.set_headers_visible(False)

        # TODO: make sure searching works
        self.fam_view.set_enable_search(True)
        self.fam_view.set_search_column(0)
        
        # signal handler
        self.fam_view.connect("cursor-changed", self.on_fam_view_select_row)
        
        # add scrollbar and pack it in
        sw = gtk.ScrolledWindow()
        sw.add(self.fam_view)
        frame_box.pack_start(sw)

        # family info box
        info_rows = { "id": "Id: ", "changed": "Last changed: ",
                      "updated": "Last updated: ", "comments": "Comments: " }
        self.fam_info = InfoExpander("More info", info_rows)
        frame_box.pack_start(self.fam_info,expand=False, fill=False)
        return frame_box

        
    def create_gen_frame(self):
        frame_box = gtk.VBox(False)

        self.gen_label = gtk.Label("Genera")
        new_button = gtk.Button("New")
        edit_button = gtk.Button("Edit")
        box = gtk.HBox(False)
        box.pack_start(self.gen_label, fill=False, expand=False)        
        box.pack_end(edit_button, fill=False, expand=False)
        box.pack_end(new_button, fill=False, expand=False)
        frame_box.pack_start(box, fill=False, expand=False)

        new_button.connect("clicked", self.on_new_gen_clicked)
        edit_button.connect("clicked", self.on_edit_gen_clicked)

        # create treeview
        self.gen_view = gtk.TreeView()
        renderer = gtk.CellRendererText()
        column = gtk.TreeViewColumn("Genera", renderer)
        column.set_cell_data_func(renderer, self.get_gen)
        self.gen_view.append_column(column)
        self.gen_view.set_headers_visible(False)
        sw = gtk.ScrolledWindow()
        sw.add(self.gen_view)        
        frame_box.pack_start(sw, fill=True, expand=True, padding=0)

        # signal handler
        self.gen_view.connect("cursor-changed", self.on_gen_view_select_row)

        # genera info box                
        info_rows = { "id": "Id: ", "changed": "Last changed: " }
        self.gen_info = InfoExpander("More info", info_rows)
        frame_box.pack_start(self.gen_info, fill=False, expand=False)
        return frame_box

    #
    # new/edit button signal handlers
    #
    def on_new(self, editor):
        e = editor()
        e.run()
        e.destroy()

        
    def on_edit(self, view, editor, table):
        selection = view.get_selection()
        model, iter = selection.get_selected()
        id = model.get_value(iter, 0).id
        sr = table.selectBy(id=id)
        #sr = tables.Plantnames.selectBy(id=id)
        e = editor(select=sr)
        e.run()
        e.destroy()
        

    def on_new_name_clicked(self, widget):
        self.on_new(PlantnamesEditor)
                

    def on_edit_name_clicked(self, widget):
        self.on_edit(self.name_view, PlantnamesEditor, tables.Plantnames)


    def on_new_acc_clicked(self, widget):
        self.on_new(AccessionsEditor)
        

    def on_edit_acc_clicked(self, widget):
        self.on_edit(self.acc_view, AccessionsEditor, tables.Accessions)
        

    def on_new_gen_clicked(self, widget):
        self.on_new(GeneraEditor)    


    def on_edit_gen_clicked(self, widget):
        self.on_edit(self.gen_view, GeneraEditor, tables.Genera)


    def on_new_fam_clicked(self, widget):
        self.on_new(FamiliesEditor)


    def on_edit_fam_clicked(self, widget):
        self.on_edit(self.fam_view, FamiliesEditor, tables.Families)