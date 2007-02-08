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
import gtk
from sqlalchemy import *
import bauble
import bauble.meta as meta
import bauble.paths as paths
import bauble.utils as utils
from bauble.utils.log import log, debug
from bauble.i18n import *
import simplejson as json

plugins = []
plugins_dict = {}
commands = {}


## def create_tables(plugins=None):
##     '''
##     drop tables from the plugins, create new ones and import their default
##     values

##     @param plugins: create tables for specific plugins, default=None which
##     means create tables for all plugins
##     '''
##     debug('entered pluginmgr.create_tables()')
##     default_filenames = []
##     tables.drop
##     for p in plugins.values():
##         tables.extend(p.tables)
##         default_filenames.extend(p.default_filenames())                
##     default_basenames = [os.path.basename(f) for f in default_filenames]                        
##     # import default data
##     if len(default_filenames) > 0:
##         from bauble.plugins.imex_csv import CSVImporter
##         csv = CSVImporter()    
##         csv.start(default_filenames)
##     debug('leaving pluginmgr.create_tables()')
    

def load(path=None):
    '''
    Search the plugin path for modules that provide a plugin
    
    @param path: the path where to look for the plugins
    
    if path is a directory then search the directory for plugins
    if path is None then use the default plugins path, bauble.plugins
    '''    
    global plugins
    if path is None:
        path = os.path.join(paths.lib_dir(), 'plugins')    
    found = _find_plugins(path)        
    depends = []
    for plugin in found:
        plugins_dict[plugin.__name__] = plugin
    
    for plugin in found:
        for dep in plugin.depends:
            try:
                depends.append((plugin, plugins_dict[dep]))
            except KeyError:
                # TODO: do something, we get here if a plugin requests another
                # plugin as a dependency but the plugin that is a dependency 
                # wasn't found
                raise
    try:
        import utils.toposort
        plugins = utils.toposort.topological_sort(found, depends)
        plugins.reverse()
    except Exception, e:
        debug(e)
        raise

    # register commands
    for plugin in found:
        for cmd in plugin.commands:
            commands[cmd.command] = cmd

    return []
    
    
def init(auto_setup=False):
    '''
    initialize the module in order of dependencies
    '''
    global plugins
    try:
        registry = Registry()
    except RegistryEmptyError:
        Registry.create()
        registry = Registry()

    # find the plugins that haven't been registered
    not_registered = []
    for p in plugins:
        if p not in registry:
            not_registered.append(p)

    if len(not_registered) > 0:
        msg = _('The following plugins were found but are not registered: '\
                '\n\n%s\n\n<i>Would you like to install them now?</i>'\
                 % ', '.join([p.__name__ for p in not_registered]))
        default_filenames = []
        if auto_setup or utils.yes_no_dialog(msg):            
            for p in not_registered:
                default_filenames.extend(p.default_filenames())
                registry.add(RegistryEntry(name=p.__name__, version='0.0'))
            if len(default_filenames) > 0:
                from bauble.plugins.imex_csv import CSVImporter            
                csv = CSVImporter()
                csv.start(default_filenames, callback=registry.save)
            else:
                registry.save()                
    #registry.save()    
    for entry in registry:
        plugins_dict[entry.name].init()
    

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
        obj = meta.BaubleMeta(name=meta.REGISTRY_KEY, value='[]')
        session = create_session()
        session.save(obj)
        session.flush()
        session.close()
    
    
    def save(self):
        '''
        save the state of the registry object to the database
        '''
        dumped = json.dumps(self.entries.values())
        obj = self.session.query(meta.BaubleMeta).get_by(name=meta.REGISTRY_KEY)
        obj.value = dumped
        self.session.flush()
        self.session.close()
        
        
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
            raise KeyError('%s already exists in the plugin registry' % entry.name)
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
#    editors = []
    tools = []
    depends = []
#    cmds = {}

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
    
    
##
## a static class that intializes a plugin
##
#class Plugin:
#
#    '''
#    label should be a unique string from other plugins, if not a Plugin
#    error will be raised
#    '''
#    label = ''
#    
#    # this could just be a list of module names instead of plugin class name
#    # to make uniqueness easier, e.g. 'org.belizebotanic.bauble.garden'
#    depends = [] # a list of plugins this plugin depends on
#    
#    enabled = False
#    
#    @classmethod
#    def init(cls):
#        register_command()    
        
    
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
        '''
        if a class extends this View and provides it's own __init__ it *must*
        call it's parent (this) __init__
        '''
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

#class FormatterPlugin(Plugin):
#
#    '''
#    formatter modules should implement this interface
#    NOTE: the title class attribute must be a unique string
#    '''
#        
#    title = ''
#    
#    @staticmethod
#    def get_settings_box():
#        '''
#        return a class that implement gtk.Box that should hold the gui for
#        the formatter modules
#        '''
#        raise NotImplementedError
#    
#    @staticmethod
#    def format(selfobjs, **kwargs):
#        '''
#        called when the use clicks on OK, this is the worker
#        '''
#        raise NotImplementedError



def _find_module_names(path):
    '''
    @param path: where to look for modules
    '''
    assert(path is not None)
    modules = []
    #path, name = os.path.split(__file__)
    if path.find("library.zip") != -1: # using py2exe
        pkg = "bauble.plugins"
        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
        x = [zipfiles[file][0] for file in zipfiles.keys() if "bauble\\plugins" in file]
        s = os.path.join('.+?', pkg, '(.+?)', '__init__.py[oc]')
        rx = re.compile(s.encode('string_escape'))
        for filename in x:
            m = rx.match(filename)
            if m is not None:
                modules.append('%s.%s' % (pkg, m.group(1)))
    else:
        for d in os.listdir(path):
            #full = path + os.sep + d
            full = os.path.join(path, d)            
            if os.path.isdir(full) and os.path.exists(os.path.join(full, "__init__.py")):
                modules.append(d)
    return modules


def _find_plugins(path):
    
    plugin_names = _find_module_names(path)

    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    import imp
    
    fp, path, desc = imp.find_module('bauble')
    bauble_module = imp.load_module('bauble', fp, path, desc)
#    fp.close()
    search_path = [os.path.join(p, 'plugins') for p in bauble_module.__path__]
    fp, path, desc = imp.find_module('plugins', bauble_module.__path__)    
    plugin_module = imp.load_module('bauble.plugins', fp, path, desc)
#    fp.close()
    
    for name in plugin_names:
        # Fast path: see if the module has already been imported.
#        if name in sys.modules:
#            mod = sys.modules[name]
        if False:
            pass
        else:
            try:
                fp, path, desc = imp.find_module(name, plugin_module.__path__)
                mod = imp.load_module('bauble.plugins.%s' % name, fp, path, desc)
            except Exception, e:
                msg = _("Could not import the %s module.\n\n%s" % (name, e))
                utils.message_details_dialog(msg, str(traceback.format_exc()), 
                         gtk.MESSAGE_ERROR)
#                if fp is not None:
#                    fp.close()
                raise        
#        debug('mod.name: %s' % mod)        
        if hasattr(mod, "plugin"):
#            debug('plugin: %s' % mod.plugin)
            plugins.append(mod.plugin)
    return plugins


#
# This implementation of topological sort was taken directly from...
# http://www.bitformation.com/art/python_toposort.html
#
def topological_sort(items, partial_order): 
    """
    Perform topological sort. 
    
    @param items: a list of items to be sorted. 
    @param partial_order: a list of pairs. If pair (a,b) is in it, it means that 
    item a should appear before item b. Returns a list of the items in one of 
    the possible orders, or None if partial_order contains a loop. """  
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
    

    
