#
# __init__.py -- tag plugin
#
# Description:
#
import os
import traceback

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import SQLError, InvalidRequestError

import bauble
import bauble.db as db
from bauble.i18n import *
import bauble.pluginmgr as pluginmgr
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import debug, warning, sa_echo, echo
from bauble.view import SearchView, MapperSearch


# TODO: is it  possible to add to a context menu for any object that shows a
# submenu of all the tags on an object

# TODO: the unicode usage here needs to be reviewed

# def edit_callback(value):
#     session = bauble.Session()
#     e = TagEditor(model_or_defaults=session.merge(value))
#     return e.start() != None


def remove_callback(value):
    s = '%s: %s' % (value.__class__.__name__, str(value))
    msg = _("Are you sure you want to remove %s?") % s
    if not utils.yes_no_dialog(msg):
        return
    try:
        session = bauble.Session()
        obj = session.query(Tag).get(value.id)
        session.delete(obj)
        session.commit()
    except Exception, e:
        msg = _('Could not delete.\n\n%s') % utils.xml_safe_utf8(e)
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     type=gtk.MESSAGE_ERROR)

    # reinitialize the tag menu
    _reset_tags_menu()
    return True


tag_context_menu = [#('Edit', edit_callback),
                    #('--', None),
                    ('Remove', remove_callback)]


class TagItemGUI:
    '''
    interface for tagging individual items in the results of the SearchView
    '''
    def __init__(self, values):
        glade_file = os.path.join(paths.lib_dir(), 'plugins', 'tag',
                                  'tag.glade')
        self.glade_xml = gtk.glade.XML(glade_file)
        self.dialog = self.glade_xml.get_widget('tag_item_dialog')
        self.dialog.set_transient_for(bauble.gui.window)
        self.item_data_label = self.glade_xml.get_widget('items_data')
        self.values = values
        self.item_data_label.set_text(', '.join([str(s) for s in self.values]))
        button = self.glade_xml.get_widget('new_button')
        button.connect('clicked', self.on_new_button_clicked)


    def on_new_button_clicked(self, *args):
        '''
        create a new tag name
        '''
        d = gtk.Dialog(_("Enter a tag name"), None,
                       gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
                       (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        d.set_default_response(gtk.RESPONSE_ACCEPT)
        d.set_default_size(250,-1)
        entry = gtk.Entry()
        entry.connect("activate",
                      lambda entry: d.response(gtk.RESPONSE_ACCEPT))
        d.vbox.pack_start(entry)
        d.show_all()
        d.run()
        name = unicode(entry.get_text(), encoding='utf-8')
        d.destroy()

        #stmt = tag_table.select(tag_table.c.tag==name).alias('_dummy').count()
        session = bauble.Session()
        ntags = session.query(Tag).filter_by(tag=name).count()
        if name not in ('', u'') and ntags == 0:
            session.add(Tag(tag=name))
            session.commit()
            model = self.tag_tree.get_model()
            model.append([False, name])
            _reset_tags_menu()


    def on_toggled(self, renderer, path, data=None):
        '''
        tag or untag the objs in self.values
        '''
        active = not renderer.get_active()
        model = self.tag_tree.get_model()
        iter = model.get_iter(path)
        model[iter][0] = active
        name = model[iter][1]
        if active:
            tag_objects(name, self.values)
        else:
            untag_objects(name, self.values)


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
        if the user hits the delete key on a selected tag in the tag editor
        then delete the tag
        '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname != "Delete":
            return
        model, row_iter = self.tag_tree.get_selection().get_selected()
        tag_name = model[row_iter][1]
        msg = _('Are you sure you want to delete the tag "%s"?') % tag_name
        if not utils.yes_no_dialog(msg):
            return
        try:
            session = bauble.Session()
            query = session.query(Tag)
            tag = query.filter_by(tag=unicode(tag_name)).one()
            session.delete(tag)
            session.commit()
            model.remove(row_iter)
            _reset_tags_menu()
            view = bauble.gui.get_view()
            if isinstance(view, SearchView):
                view.reset_view()
        except Exception, e:
            utils.message_details_dialog(utils.xml_safe(str(e)),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)


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
        item_tags = get_tag_ids(self.values)
        has_tag = False
        tag_query = bauble.Session().query(Tag)
        for tag in tag_query:
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


class Tag(db.Base):
    __tablename__ = 'tag'
    __mapper_args__ = {'order_by': 'tag'}

    # columns
    tag = Column(Unicode(64), unique=True, nullable=False)
    description = Column(Unicode)

    # relations
    _objects = relation('TaggedObj', cascade='all, delete-orphan',
                        backref='tag')


    def __str__(self):
        return str(self.tag)

    def markup(self):
        return '%s Tag' % self.tag

    def _get_objects(self):
        return get_tagged_objects(self)
    objects = property(_get_objects)


class TaggedObj(db.Base):
    __tablename__ = 'tagged_obj'

    # columns
    obj_id = Column(Integer, autoincrement=False)
    obj_class = Column(String(128))
    # # TODO: can class names be unicode, i.e. should obj_class be unicode
    tag_id = Column(Integer, ForeignKey('tag.id'))


    def __str__(self):
        return '%s: %s' % (self.obj_class.__name__, self.obj_id)


# TODO: maybe we shouldn't remove the obj from the tag if we can't
# find it, it doesn't really hurt to have it there and in case the
# table isn't available at the moment doesn't mean it won't be there
# later

# TODO: provide another function that returns (table, id) pairs that
# this function can use so that we can expose that functionality
def _get_tagged_object_pairs(tag):
    """
    @param tag: a Tag instance
    """
    from bauble.view import SearchView
    kids = []
    for obj in tag._objects:
        try:
            # __import__ "from_list" parameters has to be a list of strings
            module_name, part, cls_name = str(obj.obj_class).rpartition('.')
            module = __import__(module_name, globals(), locals(),
                                module_name.split('.')[1:])
            cls = getattr(module, cls_name)
            kids.append((cls, obj.obj_id))
        except KeyError, e:
            warning('KeyError -- tag.get_tagged_objects(%s): %s' % (tag, e))
            continue
        except SQLError, e:
            warning('SQLError -- tag.get_tagged_objects(%s): %s' % (tag, e))
            continue
        except AttributeError, e:
            warning('AttributeError -- tag.get_tagged_objects(%s): %s' \
                    % (tag, e))
            warning('Could not get the object for %s.%s(%s)' % \
                    (module_name, cls_name, obj.obj_id))
            continue

    return kids


def get_tagged_objects(tag, session=None):
    """
    Return all object tagged with tag.
    """
    if session is None:
        if isinstance(tag, Tag):
            session = object_session(tag)
        else:
            session = bauble.Session()
    if isinstance(tag, Tag):
        t = tag
    else:
        t = session.query(Tag).filter_by(tag=utils.utf8(tag)).one()

    return [session.query(mapper).filter_by(id=obj_id).one() \
            for mapper, obj_id in _get_tagged_object_pairs(t)]
#     return [session.load(mapper, obj_id) for mapper, obj_id \
#             in _get_tagged_object_pairs(t)]


def untag_objects(name, objs):
    """
    @param name:
    @param objs:

    untag objs
    """
    # TODO: should we loop through objects in a tag to delete
    # the TaggedObject or should we delete tags is they match
    # the tag in TaggedObj.selectBy(obj_class=classname, obj_id=obj.id)
    session = bauble.Session()
    try:
        #tag = session.query(Tag).filter(tag_table.c.tag==unicode(name)).one()
        tag = session.query(Tag).filter_by(tag=utils.utf8(name)).one()
    except Exception, e:
        debug(traceback.format_exc())
        return
    same = lambda x, y: x.obj_class==_classname(y) and x.obj_id==y.id
    for obj in objs:
        for kid in tag._objects:
            # x = kid
            # y = obj
            if same(kid, obj):
                #o = session.load(type(kid), kid.id)
                o = session.query(type(kid)).filter_by(id=kid.id).one()
                session.delete(o)
    session.commit()
    session.close()


# create the classname stored in the tagged_obj table
_classname = lambda x: unicode('%s.%s', 'utf-8') % (type(x).__module__, type(x).__name__)

def tag_objects(name, objs):
    '''
    @param name: the tag name, if its a str object then it will be
    converted to unicode() using the default encoding
    @type name: string
    @param obj: the object to tag
    @type obj: a list of mapper objects
    @return: the tag
    '''
    session = bauble.Session()
    if not isinstance(name, unicode):
        name = unicode(name, 'utf-8')
    try:
        tag = session.query(Tag).filter_by(tag=name).one()
    except InvalidRequestError, e:
        tag = Tag(tag=name)
        session.add(tag)
    for obj in objs:
        cls = and_(TaggedObj.obj_class==_classname(obj),
                   TaggedObj.obj_id==obj.id,
                   TaggedObj.tag_id==tag.id)
        # SA 0.4.3 gave an error without this _dummy alias
        #if tagged_obj_table.select(cls).alias('_dummy').count().scalar() == 0:
        ntagged = session.query(TaggedObj).filter(cls).count()
        if ntagged == 0:
            tagged_obj = TaggedObj(obj_class=_classname(obj), obj_id=obj.id,
                                   tag=tag)
            session.add(tagged_obj)
    # if a new tag is created with the name parameter it is always saved
    # regardless of whether the objects are tagged
    session.commit()
    session.close()


def get_tag_ids(objs):
    """
    @param objs: a list or tuple of objects

    Return a list of tag id's for tags associated with obj, only returns those
    tag ids that are common between all the objs
    """
    # TODO: this function does intersection in the most
    # straightforward way and could probably do with some optimization
    #clause = lambda x: and_(TaggedObj.obj_class==_classname(x),
    #                        TaggedObj.obj_id==x.id)
    #ors = or_(*map(clause, objs))
    session = bauble.Session()
    s = set()
    tag_id_query = session.query(Tag.id).join('_objects')
    for obj in objs:
        clause = and_(TaggedObj.obj_class==_classname(obj),
                      TaggedObj.obj_id==obj.id)
        tags = [r[0] for r in tag_id_query.filter(clause)]
        if len(s) == 0:
            s.update(tags)
        else:
            s.intersection_update(tags)
    return list(s)


def _on_add_tag_activated(*args):
    # get the selection from the search view
    # TODO: would be better if we could set the sensitivity of the menu
    # item depending on if something was selected in the search view, this
    # means we need to add more hooks to the search view or include the
    # tag plugin into the search view
    view = bauble.gui.get_view()
    if isinstance(view, SearchView):
        values = view.get_selected_values()
        if len(values) == 0:
            msg = _('Nothing selected')
            utils.message_dialog(msg)
            return
        # right now we can only tag a single item at a time, if we did
        # the f-spot style quick tagging then it would be easier to handle
        # multiple tags at a time, we could do it we would just have to find
        # the common tags for each of the selected items and then select them
        # but grey them out so you can see that some of the items have that
        # tag but not all of them
        tagitem = TagItemGUI(values)
        tagitem.start()
    #lse:
        #ig = 'Not a SearchView'
        #tils.message_dialog(msg)


def _tag_menu_item_activated(widget, tag_name):
    bauble.gui.send_command('tag="%s"' % tag_name)
    from bauble.view import SearchView
    view = bauble.gui.get_view()
    if isinstance(view, SearchView):
        view.results_view.expand_to_path('0')



_tags_menu_item = None

def _reset_tags_menu():
    tags_menu = gtk.Menu()
    add_tag_menu_item = gtk.MenuItem(_('Tag Selection'))
    add_tag_menu_item.connect('activate', _on_add_tag_activated)
    accel_group = gtk.AccelGroup()
    bauble.gui.window.add_accel_group(accel_group)
    add_tag_menu_item.add_accelerator('activate', accel_group, ord('T'),
                                      gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
    tags_menu.append(add_tag_menu_item)

    #manage_tag_item = gtk.MenuItem('Manage Tags')
    #tags_menu.append(manage_tag_item)
    tags_menu.append(gtk.SeparatorMenuItem())
    session = bauble.Session()
    query = session.query(Tag)
    try:
        for tag in query:
            item = gtk.MenuItem(tag.tag, use_underline=False)
            item.connect("activate", _tag_menu_item_activated, tag.tag)
            tags_menu.append(item)
    except:
        debug(traceback.format_exc())
        msg = _('Could not create the tags menus')
        utils.message_details_dialog(msg, traceback.format_exc(),
                                     gtk.MESSAGE_ERROR)
    #	raise
            #debug('** maybe the tags table hasn\'t been created yet')

    global _tags_menu_item
    if _tags_menu_item is None:
        _tags_menu_item = bauble.gui.add_menu(_("Tags"), tags_menu)
    else:
        _tags_menu_item.remove_submenu()
        _tags_menu_item.set_submenu(tags_menu)
        _tags_menu_item.show_all()
    session.close()


def natsort_kids(kids):
    return lambda(parent): sorted(getattr(parent, kids),key=utils.natsort_key)


class TagPlugin(pluginmgr.Plugin):

    #tables = [tag_table, tagged_obj_table]

    @classmethod
    def init(cls):
        from bauble.view import SearchView
        mapper_search = SearchView.get_search_strategy('MapperSearch')
        mapper_search.add_meta(('tag', 'tags'), Tag, ['tag'])
        SearchView.view_meta[Tag].set(children=natsort_kids('objects'),
                                      context_menu=tag_context_menu)
        if bauble.gui is not None:
            _reset_tags_menu()

    # TODO: why do we have this start() method, when does it ever get
    # called...commented out on 10/6/2008
#     @classmethod
#     def start(cls):
#         _reset_tags_menu()


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


