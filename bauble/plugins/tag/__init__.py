#
# tag module
#
import os, traceback
import gtk
from sqlalchemy import *
from sqlalchemy.orm.session import object_session
from bauble.plugins import BaublePlugin, plugins, views, tables
import bauble.paths as paths
import bauble.utils as utils
import bauble
from bauble.utils.log import debug

# TODO: i wander if it's possible to add to a context menu for any object
# that show's a submenu of all the tags on an object

def edit_callback(row):
    value = row[0]
    e = TagEditor(model_or_defaults=value)
    return e.start() != None
    
    
def remove_callback(row):
    value = row[0]    
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = "Are you sure you want to remove %s?" % s
    if not utils.yes_no_dialog(msg):
        return    
    try:
        session = create_session()
        obj = session.load(value.__class__, value.id)
        session.delete(obj)
        session.flush()
    except Exception, e:
        msg = 'Could not delete.\nn%s' % str(e)        
        utils.message_details_dialog(msg, traceback.format_exc(), 
                                     type=gtk.MESSAGE_ERROR)
        
    # reinitialize the tag menu
    _reset_tags_menu()
    return True


tag_context_menu = [('Edit', edit_callback),
                    ('--', None),
                    ('Remove', remove_callback)]

class TagItemGUI:
    '''
    interface for tagging individual items in the results of the SearchView
    '''
    # TODO: close on 'escape'
    def __init__(self, item):
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'tag', 'tag.glade')
        self.glade_xml = gtk.glade.XML(glade_file)
        self.dialog = self.glade_xml.get_widget('tag_item_dialog')
        self.dialog.set_transient_for(bauble.app.gui.window)
        self.item_data_label = self.glade_xml.get_widget('items_data')
        self.item = item
        self.item_data_label.set_text(str(self.item))            
        button = self.glade_xml.get_widget('new_button')
        button.connect('clicked', self.on_new_button_clicked)
        
        
    def on_new_button_clicked(self, *args):
        '''
        create a new tag name
        '''
        d = gtk.Dialog("Enter a connection name", None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.connect("activate", lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        name = entry.get_text()
        d.destroy()
        
        if name is not '' and tag_table.select(tag_table.c.tag==name).count().scalar() == 0:
            session = create_session()
            session.save(Tag(tag=name))
            session.flush()
            model = self.tag_tree.get_model()
            model.append([False, name])
            _reset_tags_menu()

    def on_toggled(self, renderer, path, data=None):
        '''
        add tag to self.item
        '''
        active = not renderer.get_active()
        model = self.tag_tree.get_model()
        iter = model.get_iter(path)
        model[iter][0] = active
        name = model[iter][1]
        if active:
            tag_object(name, self.item)
        else:
            untag_object(name, self.item)
            
                    
    def build_tag_tree_columns(self):
        # the toggle column
        renderer = gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_toggled)
        renderer.set_property('activatable', True)        
        toggle_column = gtk.TreeViewColumn(None, renderer)        
        toggle_column.add_attribute(renderer, "active", 0)
        
        renderer = gtk.CellRendererText()
        tag_column = gtk.TreeViewColumn(None, renderer, text=1)        
        
        return [toggle_column, tag_column]


    def on_key_released(self, widget, event):
        '''
        on delete remove the currently select tag
        '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname != "Delete":
            return        
        model, iter = self.tag_tree.get_selection().get_selected()
        tag = model[iter][1]                
        msg = 'Are you sure you want to delete the tag "%s"?' % tag
        if utils.yes_no_dialog(msg):
            t = Tag.byTag(tag)
            t.destroySelf()
            model.remove(iter)
            _reset_tags_menu()
            view = bauble.app.gui.get_current_view()
            view.refresh_search()
    
    
    def start(self):        
        # we keep restarting the dialog here since the gui was created with
        # glade then the 'new tag' button emits a response we want to ignore
        
        self.tag_tree = self.glade_xml.get_widget('tag_tree')
        
        # remove the columns from the tree
        for c in self.tag_tree.get_columns():
            tag_tree.remove_column(c)
        
        # make the new columns
        columns = self.build_tag_tree_columns()
        for col in columns:
            self.tag_tree.append_column(col)
            
        # create the model    
        model = gtk.ListStore(bool, str)
        item_tags = get_tag_ids(self.item)
        has_tag = False
        tag_query = create_session().query(Tag)                
        for tag in tag_query.select():
            if tag.id in item_tags:
                has_tag = True
            model.append([has_tag, tag.tag])
            has_tag = False
        self.tag_tree.set_model(model)
        
        self.tag_tree.add_events(gtk.gdk.KEY_RELEASE_MASK)
        self.tag_tree.connect("key-release-event", self.on_key_released)
        
        response = self.dialog.run()
        while response != gtk.RESPONSE_OK \
          and response != gtk.RESPONSE_DELETE_EVENT:            
            response = self.dialog.run()
            
        self.dialog.destroy()


#
# tag table
#
tag_table = Table('tag',
                  Column('id', Integer, primary_key=True),
                  Column('tag', Unicode(64), unique=True, nullable=False))

class Tag(bauble.BaubleMapper):
    
    def __str__(self):
        return self.tag
    
    def markup(self):
        return '%s Tag' % self.tag
    
#
# tagged_obj table
#
# TODO: can class names be unicode, i.e. should obj_class be unicode
tagged_obj_table = Table('tagged_obj',
                         Column('id', Integer, primary_key=True),
                         Column('obj_id', Integer),
                         Column('obj_class', String(64)),
                         Column('tag_id', Integer, ForeignKey('tag.id')))

class TaggedObj(bauble.BaubleMapper):
    
    def __str__():
        return '%s: %s' % (self.obj_class.__name__, self.obj_id)
        
mapper(TaggedObj, tagged_obj_table)
mapper(Tag, tag_table,
       properties={'objects': relation(TaggedObj, backref='tag', private=True)},
       order_by='tag')
        
            
def untag_object(name, so_obj):
    # TODO: should we loop through objects in a tag to delete
    # the TaggedObject or should we delete tags is they match
    # the tag in TaggedObj.selectBy(obj_class=classname, obj_id=so_obj.id)
    tag = None
    try:
        tag = Tag.byTag(name)
    except SQLObjectNotFound:
        return
    for obj in tag.objects:
        # x = obj
        # y = so_obj
        same = lambda x, y:x.obj_class==y.__class__.__name__ and x.obj_id==y.id        
        if same(obj, so_obj):
            obj.destroySelf()
            
       
def tag_object(name, so_obj):     
    session = create_session()
    tag = session.query(Tag).select_by(tag=name)[0]
    classname = so_obj.__class__.__name__
    if tagged_obj_table.select(and_(tagged_obj_table.c.obj_class==classname,
                                    tagged_obj_table.c.obj_id==so_obj.id, 
                                    tagged_obj_table.c.tag_id==tag.id)).count().scalar() == 0:
        tagged_obj = TaggedObj(obj_class=classname, obj_id=so_obj.id, tag=tag)
        session.save(tagged_obj)
        session.flush()


def get_tag_ids(so_obj):
    classname = so_obj.__class__.__name__
    query = object_session(so_obj).query(TaggedObj)
    tagged_objs = query.select_by(obj_class=classname, obj_id=so_obj.id)    
    ids = []
    for obj in tagged_objs:
        ids.append(obj.tag.id)
    return ids

    

# this should create a table tag_plant or plant_tag something like that,
# but what if we want to dump the database and keep these relations

# also, this wouldn't really be useful unless we could tag multiple types
# of items like species, accessions, plants but how do you we do joins on
# multiple types unless we have a PlantTag, AccessionTag and SpeciesTag
# we could manage 

def _on_add_tag_activated(*args):
    # get the selection from the search view
    # TODO: would be better if we could set the sensitivity of the menu
    # item depending on if something was selected in the search view, this
    # means we need to add more hooks to the search view or include the
    # tag plugin into the search view
    view = bauble.app.gui.get_current_view()
    if 'SearchView' in views and isinstance(view, views['SearchView']):
        items = view.get_selected() # right
        if len(items) == 0:
            msg = 'Nothing selected'
            utils.message_dialog(msg)
            return
        # right now we can only tag a single item at a time, if we did
        # the f-spot style quick tagging then it would be easier to handle
        # multiple tags at a time, we could do it we would just have to find
        # the common tags for each of the selected items and then select them
        # but grey them out so you can see that some of the items have that
        # tag but not all of them
        tagitem = TagItemGUI(items[0]) 
        tagitem.start()
    else:
        msg = 'Not a SearchView'
        utils.message_dialog(msg)
    
    
def _tag_menu_item_activated(widget, tag_name):
    view = bauble.app.gui.get_current_view()
    if 'SearchView' in views and isinstance(view, views['SearchView']):
        view.search('tag=%s' % tag_name)
    
    
_tags_menu_item = None

def _reset_tags_menu():    
    tags_menu = gtk.Menu()
    add_tag_item = gtk.MenuItem('Tag Selection')
    add_tag_item.connect('activate', _on_add_tag_activated)
    accel_group = gtk.AccelGroup()
    add_tag_item.add_accelerator("activate", accel_group, ord('T'),
                                   gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
    bauble.app.gui.window.add_accel_group(accel_group)        
    tags_menu.append(add_tag_item)
        
    #manage_tag_item = gtk.MenuItem('Manage Tags')
    #tags_menu.append(manage_tag_item)
    tags_menu.append(gtk.SeparatorMenuItem())
    session = create_session()
    query = session.query(Tag)
    try:
        #for tag in tag_.select():
        for tag in query.select():
            item = gtk.MenuItem(tag.tag)            
            item.connect("activate", _tag_menu_item_activated, tag.tag)
            tags_menu.append(item)
    except:
    	debug(traceback.format_exc())
    	msg = "There was a problem creating the Tags menu"
    	utils.message_details_dialog(msg, traceback.format_exc(), 
    				     gtk.MESSAGE_ERROR)
    #	raise
            #debug('** maybe the tags table hasn\'t been created yet')
         
        # TODO: this was in the pre-SQLAlchemy version but I don't
        # think the equivalent really needs to be here any more since we 
        # aren't changeing the database, in fact we never were
    	#sqlhub.processConnection.rollback()
    	#sqlhub.processConnection.begin()
	# FIXME: if we get here then the next we do with a transaction will 
	# fail which means that and exception here makes the entire program 
	# fail, we need to do something about this

    global _tags_menu_item
    if _tags_menu_item is None:
        _tags_menu_item = bauble.app.gui.add_menu("Tags", tags_menu)
    else:
        _tags_menu_item.remove_submenu()
        _tags_menu_item.set_submenu(tags_menu)
        _tags_menu_item.show_all()
        


class TagPlugin(BaublePlugin):
    
    tables = [Tag, TaggedObj]
    depends = ('SearchViewPlugin',)
    
    @classmethod
    def init(cls):
        if "SearchViewPlugin" in plugins:
            from bauble.plugins.searchview.search import SearchMeta, SearchView
            
            search_meta = SearchMeta("Tag", ["tag"], "tag")
            SearchView.register_search_meta("tag", search_meta)
            
            def get_objects(tag):                
                kids = []
                session = object_session(tag)
                for obj in tag.objects:
                    try:
                        cls = tables[obj.obj_class]
                        # TODO: if load raises an exception we should show
                        # a message and remove the obj from the tag
                        kids.append(session.load(cls, obj.obj_id))                    
                    except Exception, e:
                        msg = 'Could not the get object that this tag refers to. '\
                        'Removing tag from object %s(%s).' % (obj.obj_class, obj.obj_id)
                        utils.message_details_dialog(msg, traceback.format_exc(), gtk.MESSAGE_WARNING)
                        session.delete(obj)
                        debug(traceback.format_exc)
                return kids
                                
            SearchView.view_meta["Tag"].set(children=get_objects, 
                                            context_menu=tag_context_menu)
        
            
    @classmethod
    def create_tables(cls):
        super(TagPlugin, cls).create_tables()
        if bauble.app.gui is not None:
            _reset_tags_menu() 
        
        
    @classmethod
    def start(cls):    
        _reset_tags_menu() 
        
        
#class TagEditorView(GenericEditorView):
#    pass
#
#class TagEditorPresenter(GenericEditorPresenter):
#    pass
#
#class TagEditor(GenericModelViewPresenterEditor):
#    
#    # TODO: the tag editor allows tags to be added or removed from 
#    # a single object
#    def __init__(self, model=None, parent=None):
#        '''
#        @param model: Accession instance or None
#        @param parent: the parent widget
#        '''        
#        if model is None:
#            model = Tag()
#        GenericModelViewPresenterEditor.__init__(self, model, parent)
    
plugin = TagPlugin



