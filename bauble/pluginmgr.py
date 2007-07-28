#
# pluginmgr.py
#

# TODO: need a way to add tables to the database base without creating a new
# database completely, in case someone drops in a plugin we can create the
# needed tables

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

# TODO: need a way to register editors with the insert menu

import os
import sys
import traceback
import re
import shelve
import inspect
import gobject, gtk
from sqlalchemy import *
import bauble
import bauble.meta as meta
import bauble.paths as paths
import bauble.utils as utils
import bauble.utils.log as logger
from bauble.utils.log import log, debug, warning
from bauble.i18n import *
import simplejson as json
import logging

# TODO: we need to clarify what's in plugins, should we be looking in plugins
# or the registry for plugins, should only registered plugins be in plugins?

plugins = []
plugins_dict = {}
commands = {}

#def register_command(command, handler):
def register_command(handler):
    global commands
    if isinstance(handler.command, str):
        if handler.command in commands:
            raise ValueError(_('%s already registred' % command))
        commands[handler.command] = handler
    else:
        for cmd in handler.command:
            if cmd in commands:
                raise ValueError(_('%s already registred' % command))
            commands[cmd] = handler




def install(plugins_to_install, import_defaults=True, force=False):
    """
    @param plugins_to_install: a list of plugins to install, if None then
    install all plugins that haven't been installed
    """
    # create the registry if it doesn't exist
    transaction = default_metadata.engine.contextual_connect().begin()
    try:
        registry = Registry()
    except RegistryEmptyError:
        Registry.create()
        registry = Registry()

    if plugins_to_install is 'all':
        to_install = plugins
    else:
        to_install = plugins_to_install

    #debug('to_install: %s' % to_install)
    # import default data for plugins
    if import_defaults:
        default_filenames = []
        for p in to_install:
            default_filenames.extend(p.default_filenames())

        _error = False
        if len(default_filenames) > 0:
            from bauble.plugins.imex.csv_ import CSVImporter
            csv = CSVImporter()
#            debug('starting import')
            try:
                csv.start(filenames=default_filenames, metadata=
                          default_metadata, force=force)

                # register plugin as installed
                for p in to_install:
#                    debug('add %s to registry' % p)
                    registry.add(RegistryEntry(name=p.__name__, version='0.0'))
                    registry.save()
            except Exception, e:
                debug(e)
                transaction.rollback()
    else:
        for p in to_install:
#            debug('add %s to registry' % p)
            registry.add(RegistryEntry(name=p.__name__, version='0.0'))
            registry.save()
#    debug('commiting in pluginmgr.install()')
    transaction.commit()



def load(path=None):
    '''
    Search the plugin path for modules that provide a plugin

    @param path: the path where to look for the plugins

    if path is a directory then search the directory for plugins
    if path is None then use the default plugins path, bauble.plugins
    '''
    global plugins
    if path is None:
        if bauble.main_is_frozen():
            path = os.path.join(paths.lib_dir(), 'library.zip')
        else:
            path = os.path.join(paths.lib_dir(), 'plugins')
    found = _find_plugins(path)
    depends = []
    for plugin in found:
        plugins_dict[plugin.__name__] = plugin

    for p in found:
        for dep in p.depends:
            try:
                depends.append((p, plugins_dict[dep]))
            except KeyError:
                msg = _('The %(plugin)s plugin depends on the '\
                        '%(other_plugin)s  plugin but the %(other_plugin)s '\
                        'plugin wasn\'t found.' \
                        % {'plugin': p.__name__, 'other_plugin': dep})
                utils.message_dialog(msg, gtk.MESSAGE_WARNING)
                # TODO: do something, we get here if a plugin requests another
                # plugin as a dependency but the plugin that is a dependency
                # wasn't found
                raise
    try:
        plugins = topological_sort(found, depends)
        plugins.reverse()
#        debug(plugins)
    except Exception, e:
        debug(e)
        raise

    # register commands
    for plugin in found:
        for cmd in plugin.commands:
            register_command(cmd)

    return []


def init():
    """
    call init() for each of the plugins in the registry,
    this should be called after we have a connection to the database
    """
    registry = Registry()
    for entry in registry:
        try:
#            debug('init %s' % entry)
            plugins_dict[entry.name].init()
        except KeyError, e:
            msg = _("The %s plugin is listed in the registry but isn't " \
                    "installed\n\n" \
                    "<i>Would you like to remove this plugin from the "\
                    "registry?</i>" % entry.name)
            if utils.yes_no_dialog(msg):
                registry.remove(entry.name)
                registry.save()
        except Exception, e:
            utils.message_details_dialog(_("Error: Couldn't initialize %s\n\n"\
                                           "%s.") % (entry.name, str(e)),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)



class RegistryEmptyError(Exception):
    pass


class Registry(dict):
    '''
    manipulate the bauble plugin registry, provides a dict interface to
    XML data that is stored in the database that holds information about the
    plugins used to create the database
    '''
    def __init__(self, session=None):
        '''
        @param session: use session for the connection to the database instead
        of creating a new session, this is mostly for external tests
        '''
        if session is None:
            self.session = create_session()
        else:
            self.session = session
        result = self.session.query(meta.BaubleMeta).get_by(name=meta.REGISTRY_KEY)
        if result is None:
            raise RegistryEmptyError

        self.entries = {}
        if result.value != '[]':
            entries = json.loads(result.value)
            for e in entries:
                self.entries[e['name']] = RegistryEntry.create(e)


    def __str__(self):
        return str(self.entries.values())


    @staticmethod
    def create():
        '''
        create a new empty registry in the current database, if a registry
        already exists an error will be raised
        '''
        #logger.echo(True)
        obj = meta.BaubleMeta(name=meta.REGISTRY_KEY, value='[]')
        session = create_session()
        session.save(obj)
#        debug(obj)
        session.flush()
        #logger.echo(False)


    def save(self):
        '''
        save the state of the registry object to the database
        '''
#        logging.getLogger('sqlalchemy').setLevel(logging.DEBUG)
        dumped = json.dumps(self.entries.values())
        obj = self.session.query(meta.BaubleMeta).get_by(name=meta.REGISTRY_KEY)
        obj.value = dumped
#        debug('obj: %s=%s' % (obj.name, obj.value))
#        self.session.echo_uow = True
        self.session.flush()
        self.session.close()
#        self.session.echo_uow = False
#        logging.getLogger('sqlalchemy').setLevel(logging.WARNING)


    def __iter__(self):
        '''
        return an iterator over the registry entries
        '''
        return iter(self.entries.values())


    def __len__(self):
        '''
        return the number of entries in the registry
        '''
        return len(self.entries.values())


    def __contains__(self, plugin):
        '''
        @param plugin: either a plugin class or plugin name

        check if plugin exists in the registry
        '''
        if issubclass(plugin, Plugin):
            return plugin.__name__ in self.entries
        else:
            return plugin in self.entries


    def add(self, entry):
        '''
        @param entry: the RegistryEntry to add to the registry
        '''
        if entry in self.entries.keys():
            raise KeyError('%s already exists in the plugin registry' % \
                           entry.name)
        self.entries[entry.name] = entry


    def remove(self, name):
        '''
        remove entry with name from the registry
        '''
        self.entries.pop(name)


    def __getitem__(self, key):
        '''
        return a PluginRegistryEntry class by class name
        '''
        return self.entries[key]


    def __setitem__(self, key, entry):
        '''
        create a plugin registry entry from a kwargs
        '''
        assert isinstance(entry, RegistryEntry)
        self.entries[key] = entry



class RegistryEntry(dict):

    '''
    object to hold the registry entry data

    name, version and enabled are required
    '''
    def __init__(self, **kwargs):
        '''
        name, version and enabled are required
        '''
        assert 'name' in kwargs
        assert 'version' in kwargs
        for key, value in kwargs.iteritems():
            self[key] = value

    @staticmethod
    def create(dct):
        e = RegistryEntry(name=dct['name'], version=dct['version'])
        for key, value in dct.iteritems():
            e[key] = value
        return e

    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value



class Plugin(object):

    '''
    tables: a list of tables that this plugin provides
    tools: a list of BaubleTool classes that this plugin provides, the
        tools' category and label will be used in Bauble's "Tool" menu
    depends: a list of names classes that inherit from BaublePlugin that this
        plugin depends on
    cmds: a map of commands this plugin handled with callbacks,
        e.g dict('cmd', lambda x: handler)
    '''
    tables = []
    commands = []
    tools = []
    depends = []

    @classmethod
    def __init__(cls):
        pass

    @classmethod
    def init(cls):
        '''
        init is run when Bauble is first started
        '''
        pass


#    @classmethod
#    def start(cls):
#        '''
#        start is run after the connection to the database has been made
#        and after the interface is created but before it is shown
#        it is the last thing run before gtk.main() starts to loop
#        '''

#    @classmethod
#    def register(cls):
#        _register(cls)


#    @classmethod
#    def setup(cls):
#        '''
#        do anything that needs to be done to install the plugin, e.g. create
#        the plugins tables
#        '''
#        for t in cls.tables:
#            log.info("creating table " + t.__name__)
#            t.dropTable(ifExists=True, cascade=True)
#            t.createTable()

    @staticmethod
    def default_filenames():
        '''
        return the list of filenames to get the default data set from
        the filenames should be of the form TableClass.txt
        '''
        return []



class EditorPlugin(Plugin):
    '''
    a plugin that provides one or more editors, the editors should
    implement the Editor interface
    '''
    editors = []



class Tool(object):
    category = None
    label = None
    enabled = True
    @classmethod
    def start(cls):
        pass



class View(gtk.VBox):

    def __init__(self, *args, **kwargs):
        """
        if a class extends this View and provides it's own __init__ it *must*
        call it's parent (this) __init__
        """
        super(View, self).__init__(*args, **kwargs)



class CommandHandler(object):

    command = None

    def get_view(self):
        '''
        return the  view for this command handler
        '''
        return None

    def __call__(self, arg):
        '''
        do what this command handler does

        @param arg:
        '''
        raise NotImplementedError



def _find_module_names(path):
    '''
    @param path: where to look for modules
    '''
    modules = []
    if path.find("library.zip") != -1: # using py2exe
        warning('***** importing from library.zip needs to be reviewed since '\
                'we removed the parent parameter **********')
        raise NotImplementedError
        zipfiles = __import__(parent, globals(), locals(),
                              [parent]).__loader__._files
        x = [zipfiles[file][0] \
             for file in zipfiles.keys() if parent.replace('.', '\\') in file]
        s = os.path.join('.+?', parent, '(.+?)', '__init__.py[oc]')
        rx = re.compile(s.encode('string_escape'))
        for filename in x:
            m = rx.match(filename)
            if m is not None:
                modules.append(m.group(1))
    else:
        for dir, subdir, files in os.walk(path):
            if dir != path and '__init__.py' in files:
                modules.append(dir[len(path)+1:].replace(os.sep,'.'))
    return modules



def _find_plugins(path):
    plugins = []
    import bauble.plugins
    plugin_module = bauble.plugins
    mod = None
    plugin_names = map(lambda s: 'bauble.plugins.%s' % s,
                       _find_module_names(path))
    for name in plugin_names:
        # Fast path: see if the module has already been imported.
        if name in sys.modules:
            mod = sys.modules[name]
        else:
            try:
                mod = __import__(name, globals(), locals(), [name], -1)
            except Exception, e:
                msg = _('Could not import the %(module)s module.\n\n'\
                        '%(error)s' % {'module': name, 'error': e})
                utils.message_details_dialog(msg, str(traceback.format_exc()),
                                             gtk.MESSAGE_ERROR)
        if not hasattr(mod, "plugin"):
            continue

        # if mod.plugin is a function it should return a plugin or list of
        # plugins
        if inspect.isfunction(mod.plugin):
            mod_plugin = mod.plugin()
        else:
            mod_plugin = mod.plugin

        is_plugin = lambda p: inspect.isclass(p) and issubclass(p, Plugin)
        if isinstance(mod_plugin, (list, tuple)):
            for p in mod_plugin:
                if is_plugin(p):
                    plugins.append(p)
        elif is_plugin(mod_plugin):
            plugins.append(mod_plugin)
        else:
            warning(_('%s.plugin is not an instance of pluginmgr.Plugin'\
                      % mod.__name__))
    return plugins



#
# This implementation of topological sort was taken directly from...
# http://www.bitformation.com/art/python_toposort.html
#
def topological_sort(items, partial_order):
    """
    Perform topological sort.

    @param items: a list of items to be sorted.
    @param partial_order: a list of pairs. If pair (a,b) is in it, it means
    that item a should appear before item b. Returns a list of the items in
    one of the possible orders, or None if partial_order contains a loop.
    """
    def add_node(graph, node):
        """Add a node to the graph if not already exists."""
        if not graph.has_key(node):
            graph[node] = [0] # 0 = number of arcs coming into this node.
    def add_arc(graph, fromnode, tonode):
        """
        Add an arc to a graph. Can create multiple arcs. The end nodes must
        already exist.
        """
        graph[fromnode].append(tonode)
        # Update the count of incoming arcs in tonode.
        graph[tonode][0] = graph[tonode][0] + 1

    # step 1 - create a directed graph with an arc a->b for each input
    # pair (a,b).
    # The graph is represented by a dictionary. The dictionary contains
    # a pair item:list for each node in the graph. /item/ is the value
    # of the node. /list/'s 1st item is the count of incoming arcs, and
    # the rest are the destinations of the outgoing arcs. For example:
    # {'a':[0,'b','c'], 'b':[1], 'c':[1]}
    # represents the graph: c <-- a --> b
    # The graph may contain loops and multiple arcs.
    # Note that our representation does not contain reference loops to
    # cause GC problems even when the represented graph contains loops,
    # because we keep the node names rather than references to the nodes.
    graph = {}
    for v in items:
        add_node(graph, v)
    for a,b in partial_order:
        add_arc(graph, a, b)

    # Step 2 - find all roots (nodes with zero incoming arcs).
    roots = [node for (node,nodeinfo) in graph.items() if nodeinfo[0] == 0]

    # step 3 - repeatedly emit a root and remove it from the graph. Removing
    # a node may convert some of the node's direct children into roots.
    # Whenever that happens, we append the new roots to the list of
    # current roots.
    sorted = []
    while len(roots) != 0:
        # If len(roots) is always 1 when we get here, it means that
        # the input describes a complete ordering and there is only
        # one possible output.
        # When len(roots) > 1, we can choose any root to send to the
        # output; this freedom represents the multiple complete orderings
        # that satisfy the input restrictions. We arbitrarily take one of
        # the roots using pop(). Note that for the algorithm to be efficient,
        # this operation must be done in O(1) time.
        root = roots.pop()
        sorted.append(root)
        for child in graph[root][1:]:
            graph[child][0] = graph[child][0] - 1
            if graph[child][0] == 0:
                roots.append(child)
        del graph[root]
    if len(graph.items()) != 0:
        # There is a loop in the input.
        return None
    return sorted
