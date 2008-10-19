#
# pluginmgr.py
#

# TODO: need a way to register editors with the insert menu...could be
# done in Plugin.init()...UPDATE: 5/10.08...dont' we do this already

# TODO: don't completely blow up if there is a problem with on plugin,
# e.g. don't ask if you want to remove all the other plugins unless
# the plugin is dependent on the bad one

# TODO: currently (3/10/2008) we can drop in and remove plugins from
# bauble but still if the plugin has tables then those tables on get
# created when a new database is created, we need the ability to
# create tables on installation...one solution is to create a tables
# attribue on the plugins with a list of tables that need to be
# created, the other is to just create an install() method on the
# plugin that is called when the plugin is first installed and then we
# let the plugins handle their own table creation and default imports

# 1. load the plugins: search the plugin directory for plugins,
# populates the plugins dict
#
# 2. install the plugins if not in the registry, add properly
# installed plugins in to the registry
#
# 3. initialize the plugins

import os
import sys
import traceback
import re
import inspect
import logging

import gobject
import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from sqlalchemy.exc import *
from sqlalchemy.orm.exc import *
import simplejson as json

import bauble
#import bauble.meta as meta
from bauble.error import check, CheckConditionError, BaubleError
import bauble.paths as paths
import bauble.utils as utils
import bauble.utils.log as logger
from bauble.utils.log import log, debug, warning, error
from bauble.i18n import *

plugins = {}
commands = {}

def register_command(handler):
    """
    Register command handlers.  If a command is a duplicate then it
    will overwrite the old command of the same name.
    """
    global commands
    if isinstance(handler.command, str):
        #if handler.command in commands:
        #    raise ValueError(_('%s already registered' % handler.command))
        commands[handler.command] = handler
    else:
        for cmd in handler.command:
            #if cmd in commands:
            #    raise ValueError(_('%s already registered' % cmd))
            commands[cmd] = handler




# def install(plugins_to_install, import_defaults=True, force=False):
#     """
#     @param plugins_to_install: a list of plugins to install, if None then
#     install all plugins that haven't been installed
#     """
#     # create the registry if it doesn't exist
#     try:
#         registry = Registry()
#     except RegistryEmptyError:
#         Registry.create()
#         registry = Registry()

#     if plugins_to_install is 'all':
#         to_install = plugins.values()
#     else:
#         to_install = plugins_to_install

#     # import default data for plugins
#     session = bauble.Session()
#     from itertools import chain
#     default_filenames=list(chain(*[p.default_filenames() for p in to_install]))
#     if import_defaults and len(default_filenames) > 0:
#         from bauble.plugins.imex.csv_ import CSVImporter
#         csv = CSVImporter()
#         import_error = False
#         import_exc = None
#         try:
#             #transaction = bauble.engine.contextual_connect().begin()
#             #session = bauble.Session()
#             # cvs.start uses a task which blocks here but allows the
#             # interface to stay responsive
#             def on_import_error(exc):
#                 debug(exc)
#                 import_error = True
#                 import_exc = exc
#                 #transaction.rollback()
#                 session.rollback()
#             def on_import_quit():
#                 """
#                 register plugins and commit the imports
#                 """
#                 # register plugin as installed
#                 for p in to_install:
#                     registry.add(RegistryEntry(name=p.__name__,
#                                                version=u'0.0'))
#                 registry.save()
#                 #transaction.commit()
#                 session.commit()
# ##                debug('start import')
#             csv.start(filenames=default_filenames, metadata=bauble.metadata,
#                       force=force, on_quit=on_import_quit,
#                       on_error=on_import_error)
#         except Exception, e:
#             warning(e)
#             #transaction.rollback()
#             session.rollback()
#             raise
#     else:
#         try:
#             for p in to_install:
#                 #debug('add %s to registry' % p.__name__)
#                 registry.add(RegistryEntry(name=p.__name__, version=u'0.0'))
#                 registry.save()
#         except Exception, e:
#             debug(e)
#             #transaction.rollback()
#             session.rollback()
#             raise


def _check_dependencies(plugin):
    '''
    Check the dependencies of plugin
    '''



def _create_dependency_pairs(plugs):
    """
    Returns a tuple.  The first item in the tuple is the dependency
    pairs that can be passed to topological sort.  The second item is
    a dictionary whose keys are plugin names and value are a list of
    unmet dependencies.
    """
    depends = []
    unmet = {}
    for p in plugs:
        for dep in p.depends:
            try:
                depends.append((plugins[dep], p))
            except KeyError:
                debug('no dependency %s for %s' % (dep, p.__name__))
                u = unmet.setdefault(p.__name__, [])
                u.append(dep)
    return depends, unmet


def load(path=None):
    """
    Search the plugin path for modules that provide a plugin.

    @param path: the path where to look for the plugins

    if path is a directory then search the directory for plugins
    if path is None then use the default plugins path, bauble.plugins
    """
    if path is None:
        if bauble.main_is_frozen():
            #path = os.path.join(paths.lib_dir(), 'library.zip')
            path = os.path.join(paths.main_dir(), 'library.zip')
        else:
            path = os.path.join(paths.lib_dir(), 'plugins')
    found = _find_plugins(path)
    if len(found) == 0:
        debug('No plugins found at path: %s' % path)

    for plugin in found:
        # TODO: should we include the module name of the plugin to allow
        # for plugin namespaces or just assume that the plugin class
        # name is unique
        plugins[plugin.__name__] = plugin



def init(force=False):
    """
    Initialize the plugin manager.

    1. Check for and install any plugins in the plugins dict that
    aren't in the registry.
    2. Call each init() for each plugin the registry in order of dependency
    3. Register the command handlers in the plugin's commands[]

    NOTE: This should be called after after Bauble has established a
    connection to a database with bauble.open_database()
    """
    #debug('bauble.pluginmgr.init()')
    registry = Registry()

    # search for plugins that are in the plugins dict but not in the registry
    not_installed = [p for p in plugins.values() if p not in registry]
    if len(not_installed) > 0:
        msg = _('The following plugins were not found in the plugin '\
                 'registry:\n\n<b>%s</b>\n\n'\
                 '<i>Would you like to install them now?</i>' \
                % ', '.join([p.__name__ for p in not_installed]))
        if force or utils.yes_no_dialog(msg):
            install([p for p in not_installed])

    if len(registry) == 0:
        return

    # sort plugins in the registry by their dependencies
    registered = [plugins[e.name] for e in registry]
    deps, unmet = _create_dependency_pairs(registered)
    ordered = topological_sort(registered, deps)
    if not ordered:
        raise BaubleError(_('The plugins contain a dependency loop. This '\
                            'can happend if two plugins directly or '\
                            'indirectly rely on each other'))

    # call init() for each ofthe plugins
    for plugin in ordered:
        #debug('init: %s' % plugin)
        try:
            plugin.init()
        except KeyError, e:
            # don't removed the plugin from the registry because if we
            # find it again the user might decide to reinstall it
            # which could overwrite data
            ordered.pop(plugin)
            msg = _("The %(plugin_name)s plugin is listed in the registry "\
                    "but isn't wasn't found in the plugin directory") \
                    % dict(plugin_name=plugin.__name__)
            warning(msg)
        except Exception, e:
            #error(e)
            ordered.pop(plugin)
            error(traceback.print_exc())
            safe = utils.xml_safe_utf8
            values = dict(entry_name=plugin.__name__, exception=safe(e))
            utils.message_details_dialog(_("Error: Couldn't initialize "\
                                           "%(entry_name)s\n\n" \
                                           "%(exception)s." % values),
                                         traceback.format_exc(),
                                         gtk.MESSAGE_ERROR)


    # register the plugin commands seperately from the plugin initialization
    for plugin in ordered:
        if plugin.commands in (None, []):
            continue
        for cmd in plugin.commands:
            try:
                register_command(cmd)
            except Exception, e:
                msg = 'Error: Could not register command handler.\n\n%s' % \
                      utils.xml_safe(str(e))
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)



def install(plugins_to_install, import_defaults=True, force=False):
    """
    @param plugins_to_install: a list of plugins to install, if 'all'
    then install all plugins listed in the bauble.pluginmgr.plugins
    dict that aren't already listed in the plugin registry
    @param import_defaults: whether a plugin should import its default database
    @param force:
    """
    #debug('pluginmgr.install(%s)' % plugins_to_install)
    # create the registry if it doesn't exist
    if not Registry.exists():
        Registry.create()

    session = bauble.Session()
    registry = Registry(session)

    if plugins_to_install is 'all':
        to_install = plugins.values()
    else:
        to_install = plugins_to_install

    if len(to_install) == 0:
        # no plugins to install
        return

    # sort the plugins by their dependency
    depends, unmet = _create_dependency_pairs(to_install)
    if unmet != {}:
        debug(unmet)
        raise BaubleError('unmet dependencies')
    to_install = topological_sort(to_install, depends)
    if not to_install:
        raise BaubleError(_('The plugins contain a dependency loop. This '\
                            'can happend if two plugins directly or '\
                            'indirectly rely on each other'))

#         msg = _('The %(plugin)s plugin depends on the %(other_plugin)s '\
#                 'plugin but the %(other_plugin)s plugin wasn\'t found.') \
#                 % {'plugin': e.plugin.__name__, 'other_plugin': e.not_found}
#         utils.message_dialog(msg, gtk.MESSAGE_WARNING)

#         to_install = topological_sort(to_install, depends)
#     except DependencyError, e:
#         msg = _('The %(plugin)s plugin depends on the %(other_plugin)s '\
#                 'plugin but the %(other_plugin)s plugin wasn\'t found.') \
#                 % {'plugin': e.plugin.__name__, 'other_plugin': e.not_found}
#         utils.message_dialog(msg, gtk.MESSAGE_WARNING)
#         raise
#     except DependencyError, e:
#         error(utils.utf8(e))

    try:
        for p in to_install:
            #debug('install: %s' % p.__name__)
            p.install(import_defaults=import_defaults)
            registry.add(RegistryEntry(name=p.__name__, version=u'0.0'))
        session.commit()
    except Exception, e:
        debug(e)
        msg = _('Error installing plugins.')
        utils.message_details_dialog(msg, utils.utf8(traceback.format_exc()),
                                     gtk.MESSAGE_ERROR)
        debug(traceback.format_exc())
        session.rollback()
    finally:
        session.close()



class RegistryEmptyError(Exception):
    pass


class Registry(dict):
    """
    Manipulate the bauble plugin registry. The registry is stored in
    the bauble meta table in JSON format.  This class provides a dict
    interface to the registry.
    """
    def __init__(self, session=None):
        '''
        @param session: use session for the connection to the database instead
        of creating a new session, this is mostly for external tests
        '''
        if session is None:
            self.session = bauble.Session()
        else:
            self.session = session


    def _get_entries(self):
        import bauble.meta as meta
        try:
            result = self.session.query(meta.BaubleMeta)\
                     .filter_by(name=meta.REGISTRY_KEY).one()
        except NoResultFound, e:
            debug(e)
            raise RegistryEmptyError

        named_entries = {}
        if result.value != '[]':
            entries = json.loads(result.value)
            for e in entries:
                named_entries[e['name']] = RegistryEntry.create(e)
        return named_entries
    entries = property(_get_entries)


#     def refresh(self):
#         """
#         Refresh the registry from the database
#         """
#         import bauble.meta as meta
#         query = self.session.query(meta.BaubleMeta)
#         try:
#             result = query.filter_by(name=meta.REGISTRY_KEY).one()
#         except:
#             raise RegistryEmptyError

#         self.entries = {}
#         if result.value != '[]':
#             entries = json.loads(result.value)
#             for e in entries:
#                 self.entries[e['name']] = RegistryEntry.create(e)


    def __str__(self):
        return str(self.entries.values())


    @staticmethod
    def exists(session=None):
        """
        Test if the registry exists
        """
        import bauble.meta as meta
        if not session:
            session = bauble.Session()
        query = session.query(meta.BaubleMeta)\
                .filter_by(name=meta.REGISTRY_KEY).first()
        return query is not None


    @staticmethod
    def create(session=None):
        """
        Create a new empty registry in the current database, if a
        registry already exists an error will be raised.  If session
        is passed in then we don't commit the session.  If session is
        passed in then we commit it.
        """
        import bauble.meta as meta
        reg = meta.BaubleMeta(name=meta.REGISTRY_KEY, value=u'[]')
        if not session:
            session = bauble.Session()
            session.add(reg)
            session.commit()
        else:
            session.add(reg)


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
        if isinstance(plugin, basestring):
            return plugin in self.entries
        else:
            return plugin.__name__ in self.entries


    def add(self, entry):
        '''
        @param entry: the RegistryEntry to add to the registry
        '''
        entries = self.entries.copy()
        if entry in entries.keys():
            raise KeyError('%s already exists in the plugin registry' % \
                           entry.name)
        entries[entry.name] = entry
        import bauble.meta as meta
        dumped = json.dumps(entries.values())
        obj = self.session.query(meta.BaubleMeta).\
              filter_by(name=meta.REGISTRY_KEY).one()
        obj.value = unicode(dumped)


    def remove(self, name):
        '''
        remove entry with name from the registry
        '''
        import bauble.meta as meta
        entries = self.entries.copy()
        entries.pop(name)
        dumped = json.dumps(entries.values())
        obj = self.session.query(meta.BaubleMeta).\
              filter_by(name=meta.REGISTRY_KEY).one()
        obj.value = unicode(dumped)


    def __getitem__(self, key):
        '''
        return a PluginRegistryEntry class by class name
        '''
        return self.entries[key]



class RegistryEntry(dict):
    """
    object to hold the registry entry data

    name, version and enabled are required
    """
    def __init__(self, name, version, **kwargs):
        """
        @param name: the name of the plugin
        @param version: the plugin version
        """
        check('name' is not None)
        check('version' is not None)
        self['name'] = name
        self['version'] = version
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
    """
    tools:
      a list of BaubleTool classes that this plugin provides, the
      tools' category and label will be used in Bauble's "Tool" menu
    depends:
      a list of names classes that inherit from BaublePlugin that this
      plugin depends on
    cmds:
      a map of commands this plugin handled with callbacks,
      e.g dict('cmd', lambda x: handler)
    """
    commands = []
    tools = []
    depends = []

    @classmethod
    def __init__(cls):
        pass

    @classmethod
    def init(cls):
        '''
        init() is run when Bauble is first started
        '''
        pass

    @classmethod
    def install(cls, import_defaults=True):
        '''
        install() is run when a new plugin is installed, it is usually
        only run once for the lifetime of the plugin
        '''
        pass



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
        from zipfile import ZipFile
        z = ZipFile(path)
        filenames = z.namelist()
        rx = re.compile('(.+)\\__init__.py[oc]')
        for f in filenames:
            m = rx.match(f)
            if m is not None:
                modules.append(m.group(1).replace('/', '.')[:-1])
        z.close()
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

    if path.find('library.zip') != -1:
        plugin_names = [m for m in _find_module_names(path) \
                        if m.startswith('bauble.plugins')]
    else:
        plugin_names =['bauble.plugins.%s'%m for m in _find_module_names(path)]

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
                debug(msg)
                debug(traceback.format_exc())
#                 utils.message_details_dialog(msg, str(traceback.format_exc()),
#                                              gtk.MESSAGE_ERROR)
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
#    debug(plugins)
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
