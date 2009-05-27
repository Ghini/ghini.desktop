#
# pluginmgr.py
#

"""
Manage plugin registry, loading, initialization and installation.  The plugin manager should be started in the following order:

1. load the plugins: search the plugin directory for plugins,
populates the plugins dict (happens in load())

2. install the plugins if not in the registry, add properly
installed plugins in to the registry (happens in load())

3. initialize the plugins (happens in init())
"""

import logging
import inspect
import os
import re
import sys
import traceback
import gobject
import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
import sqlalchemy.orm.exc as orm_exc
import bauble
import bauble.db as db
from bauble.error import check, CheckConditionError, BaubleError
import bauble.paths as paths
import bauble.utils as utils
import bauble.utils.log as logger
from bauble.utils.log import log, debug, warning, error
from bauble.i18n import *

# TODO: should make plugins and ordered dict that is sorted by
# dependency, maybe use odict from
# http://www.voidspace.org.uk/python/odict.html
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
    Search the plugin path for modules that provide a plugin. If path
    is a directory then search the directory for plugins. If path is
    None then use the default plugins path, bauble.plugins.

    This method populates the pluginmgr.plugins dict and imports the
    plugins but doesn't do any plugin initialization.

    :param path: the path where to look for the plugins
    :type path: str
    """
    if path is None:
        if bauble.main_is_frozen():
            #path = os.path.join(paths.lib_dir(), 'library.zip')
            path = os.path.join(paths.main_dir(), 'library.zip')
        else:
            path = os.path.join(paths.lib_dir(), 'plugins')
    found, errors = _find_plugins(path)

    for name, exc_info in errors.iteritems():
        exc_str = utils.xml_safe_utf8(exc_info[1])
        tb_str = ''.join(traceback.format_tb(exc_info[2]))
        utils.message_details_dialog('Could not load plugin: '
                                     '\n\n<i>%s</i>\n\n%s' \
                                         % (name, exc_str),
                                     tb_str, type=gtk.MESSAGE_ERROR)

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
    connection to a database with db.open()
    """
    #debug('bauble.pluginmgr.init()')
    # ******
    # NOTE: Be careful not to keep any references to
    # PluginRegistry open here as it will cause a deadlock if you try
    # to create a new database. For example, don't query the
    # PluginRegistry with a session without closing the session.
    # ******

    # search for plugins that are in the plugins dict but not in the registry
    registered = plugins.values()
    try:
        # try to access the plugin registry, if the tables does not
        # exists then it might mean that we are opening a pre 0.9
        # database, in this case we just assume all the plugins have
        # been installed and registered, this might be the right thing
        # to do but it least it allows you to connect to a pre bauble 0.9
        # database and use it to upgrade to a >=0.9 database
        registered_names = PluginRegistry.names()
        not_installed = [p for n,p in plugins.iteritems() \
                             if n not in registered_names]
        if len(not_installed) > 0:
            msg = _('The following plugins were not found in the plugin '\
                        'registry:\n\n<b>%s</b>\n\n'\
                        '<i>Would you like to install them now?</i>' \
                        % ', '.join([p.__name__ for p in not_installed]))
            if force or utils.yes_no_dialog(msg):
                install([p for p in not_installed])
        # sort plugins in the registry by their dependencies
        for name in PluginRegistry.names():
            try:
                registered.append(plugins[name])
            except KeyError, e:
                msg = _('The following plugin is in the registry but '
                        'could not be loaded:\n\n%s' % utils.utf8(name))
                utils.message_dialog(msg, type=gtk.MESSAGE_WARNING)
    except Exception, e:
        raise

    if not registered:
        # no plugins to initialize
        return

    deps, unmet = _create_dependency_pairs(registered)
    ordered = topological_sort(registered, deps)
    if not ordered:
        raise BaubleError(_('The plugins contain a dependency loop. This '\
                                'can happen if two plugins directly or '\
                                'indirectly rely on each other'))

    # call init() for each ofthe plugins
    for plugin in ordered:
        #debug('init: %s' % plugin)
        try:
            plugin.init()
        except KeyError, e:
            # don't remove the plugin from the registry because if we
            # find it again the user might decide to reinstall it
            # which could overwrite data
            ordered.remove(plugin)
            msg = _("The %(plugin_name)s plugin is listed in the registry "\
                    "but isn't wasn't found in the plugin directory") \
                    % dict(plugin_name=plugin.__name__)
            warning(msg)
        except Exception, e:
            #error(e)
            ordered.remove(plugin)
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
    :param plugins_to_install: A list of plugins to install. If the
        string "all" is passed then install all plugins listed in the
        bauble.pluginmgr.plugins dict that aren't already listed in
        the plugin registry.

    :param import_defaults: Flag passed to the plugin's install()
        method to indicate whether it should import its default data.
    :type import_defaults: bool

    :param force:  Force, don't ask questions.
    :type force: book
    """
    #debug('pluginmgr.install(%s)' % plugins_to_install)
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
            # TODO: here we make sure we don't add the plugin to the
            # registry twice but we should really update the version
            # number in the future when we accept versioned plugins
            # (if ever)
            if not PluginRegistry.exists(p):
                PluginRegistry.add(p)
        #session.commit()
    except Exception, e:
        raise
#         msg = _('Error installing plugins: %s' % p)
#         debug(e)
#         #safe = utils.xml_safe_utf8
#         #utils.message_details_dialog(safe(msg),
#         #                             safe(traceback.format_exc()),
#         #                             gtk.MESSAGE_ERROR)
#         debug(traceback.format_exc())



class PluginRegistry(db.Base):
    """
    The PluginRegistry contains a list of plugins that have been installed
    in a particular instance of a Bauble database.  At the momeny it only
    includes the name and version of the plugin but this is likely to change
    in future versions.
    """
    __tablename__ = 'plugin'
    name = Column(Unicode(64), unique=True)
    version = Column(Unicode(12))

    @staticmethod
    def add(plugin):
        """
        Add a plugin to the registry.

        Warning: Adding a plugin to the registry does not install it.  It
        should be installed before adding.
        """
        p = PluginRegistry(name=utils.utf8(plugin.__name__),
                           version=utils.utf8(plugin.version))
        session = bauble.Session()
        session.add(p)
        session.commit()
        session.close()


    @staticmethod
    def remove(plugin):
        """
        Remove a plugin from the registry by name.
        """
        #debug('PluginRegistry.remove()')
        session = bauble.Session()
        p = session.query(PluginRegistry).\
            filter_by(name=utils.utf8(plugin.__name__)).one()
        session.delete(p)
        session.commit()
        session.close()


    @staticmethod
    def all(session=None):
        if not session:
            session = bauble.Session()
        return list(session.query(PluginRegistry))


    @staticmethod
    def names(bind=None):
        t = PluginRegistry.__table__
        results = select([t.c.name], bind=bind).execute(bind=bind)
        names = [n[0] for n in results]
        results.close()
        return names


    @staticmethod
    def exists(plugin):
        """
        Check if plugin exists in the plugin registry.
        """
        if isinstance(plugin, basestring):
            name = plugin
            version = None
        else:
            name = plugin.__name__
            version = plugin.version
        session = bauble.Session()
        try:
            session.query(PluginRegistry).\
                filter_by(name=utils.utf8(name)).one()
            return True
        except orm_exc.NoResultFound, e:
            return False
        finally:
            session.close()
            #session.close()



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
    description:
      a short description of the plugin
    """
    commands = []
    tools = []
    depends = []
    description = ''
    version = '0.0'

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

        :param arg:
        '''
        raise NotImplementedError


def _find_module_names(path):
    '''
    :param path: where to look for modules
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
    """
    Return the plugins at path.
    """
    plugins = []
    import bauble.plugins
    plugin_module = bauble.plugins
    errors = {}

    if path.find('library.zip') != -1:
        plugin_names = [m for m in _find_module_names(path) \
                        if m.startswith('bauble.plugins')]
    else:
        plugin_names =['bauble.plugins.%s'%m for m in _find_module_names(path)]

    for name in plugin_names:
        mod = None
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
                errors[name] = sys.exc_info()
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
    return plugins, errors


#
# This implementation of topological sort was taken directly from...
# http://www.bitformation.com/art/python_toposort.html
#
def topological_sort(items, partial_order):
    """
    Perform topological sort.

    :param items: a list of items to be sorted.
    :param partial_order: a list of pairs. If pair (a,b) is in it, it
        means that item a should appear before item b. Returns a list of
        the items in one of the possible orders, or None if partial_order
        contains a loop.
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
