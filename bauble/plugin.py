#
# plugin module
#

# TODO: need a way to add tables to the database base without creating a new
# database completely, in case someone drops in a plugin we can create the 
# needed tables

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

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

plugins = {}
#views = {}
#tools = {}
#editors = {}
#tables = {}

def register_command(cmd, callback):
    '''
    @param cmd: the cmd to register, to be called from the bauble entry with
    cmd=parameters
    @param callback: the method to be called when cmd is matched, signature 
    us callback(parameters)
    '''
    bauble.command_entry.register_command(cmd, callback)


def sort_dependencies():
    '''
    don't allow circular dependencies
    '''
    

def init(path=None):
    '''
    @param path: the path where to look for the plugins
    
    if path is a directory then search the directory for plugins
    if path is None then use the default plugins path, bauble.plugins
    '''
    if path is None:
        path = paths.lib_dir()
    
    found = _find_plugins(path)        
    registry = Registry()
#    for p in found:
#        plugins[p.__name__] = p
#        if p.__name__ in registry:
#            print '%s already in registry' % p.__name__            
#        else:
#            print 'adding %s to registry' % p.__name__
#            registry[p.__name__] = p
        
#class PluginError(Exception):
#    pass
#    
#class PluginInitError(PluginError):
#    pass

#class PluginRegistryError(PluginError):
#    pass
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
        
        
    @staticmethod
    def create():        
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
        return iter(self.entries.values())
        #return iter(self.entries.values())

    # TODO: could use these to enable, disable plugin on the fly, would
    # have to take immediate effect
#    def enable(self):        
#        pass
#    def disabled(self):
#        pass

    def __len__(self):
        '''
        return the number of entries in the registry
        '''
        return len(self.entries.values())
        

    def add(self, entry):
        '''
        @param entry: the RegistryEntry to add to the registry
        '''
        if entry in self.entries.keys():
            raise KeyError('%s already exists in the plugin registry' % entry.name)
        self.entries[entry.name] = entry
                        
        
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






#class PluginRegistry(dict):
#    
#    def __init__(self):
#        super(PluginRegistry, self).__init__()
#        path = os.path.join(paths.user_dir(), 'registry')
#
#        #self.registry = shelve.open(path, flag='c')
#        
#    def __getitem__(self, key):
#        return self.registry[key]
#    
#    def __setitem__(self, key, value):
#        self.registry[key] = value
#    
#    def __contains__(self, key):
#        return key in self.registry
#        #return self.registry.__contains__(key)
#    
#    def __delitem__(self, key):
#        del self.registry[key]
#    
#    def __del__(self):
#        if hasattr(self, 'registry'):
#            self.registry.close()


    
#
# a static class that intializes a plugin
#
class Plugin:

    '''
    label should be a unique string from other plugins, if not a Plugin
    error will be raised
    '''
    label = ''
    
    # this could just be a list of module names instead of plugin class name
    # to make uniqueness easier, e.g. 'org.belizebotanic.bauble.garden'
    depends = [] # a list of plugins this plugin depends on
    
    enabled = False
    
    @classmethod
    def init(cls):
        register_command()
    
class EditorPlugin(Plugin):
    '''
    a plugin that provides one or more editors, the editors should
    implement the Editor interface
    '''
    editors = []
    
class ToolPlugin(Plugin):

    category = ''
    
    @classmethod
    def init(cls):
        super(cls, Plugin).init()        
        '''
        '''
        
class FormatterPlugin(Plugin):

    '''
    formatter modules should implement this interface
    NOTE: the title class attribute must be a unique string
    '''
        
    title = ''
    
    @staticmethod
    def get_settings_box():
        '''
        return a class that implement gtk.Box that should hold the gui for
        the formatter modules
        '''
        raise NotImplementedError
    
    @staticmethod
    def format(selfobjs, **kwargs):
        '''
        called when the use clicks on OK, this is the worker
        '''
        raise NotImplementedError



def init_plugins():
    """
    initialized all the plugins in plugins
    """
    load()
    for p in plugins.values():
        p.init()
    
    
def start_plugins():
    '''
    start of the plugins
    '''
    for p in plugins.values():
        p.start()
        
        
def _register(plugin_class):        
    # check dependencies
    plugin_name = plugin_class.__name__
    #if not bauble.main_is_frozen():
    #log.info("registering " + plugin_name)
    for dependency in plugin_class.depends:            
        if dependency not in plugins:
            msg = _('Can\'t load plugin %(plugin)s. This plugin depends on the '\
                    '%(dependency)s plugin but %(dependency)s doesn\'t exist') \
                    % ({'plugin': plugin_name, 'dependency': dependency})
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            plugins.pop(plugin_name)
            return
                    
    plugins[plugin_name] = plugin_class
    
#    # add tables
#    for t in plugin_class.tables:
#        tables[t.__name__] = t
#    
#    # add tools
#    for l in plugin_class.tools:    
#        if not issubclass(l, BaubleTool):
#            raise TypeError(_('%(tool)s tool from plugin %(plugin)s is not an '\
#                            'instance of BaubleTool') % \
#                            {'tool': l, 'plugin': plugin_name})
#        tools[l.__name__] = l
#        
#    # add cmds
#    for cmd, cb in plugin_class.cmds.iteritems():
#        bauble.app.register_command(cmd, cb)


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
    print plugin_names
    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    for name in plugin_names:
        try:
            mod = __import__(name, globals(), locals(), [''])
        except Exception, e:
            msg = _("Could not import the %s module.") % name
            utils.message_details_dialog(msg, str(traceback.format_exc()), 
                     gtk.MESSAGE_ERROR)
            raise
        if hasattr(mod, "plugins"):            
            plugins.extend(mod.plugins)
    return plugins


#def load():
#    # accumulate all the plugins in the module, call the register methods
#    # once the plugins have been found, this is called at the bottom of 
#    # this file
#    found = _find_plugins()
#    for p in found:                
#        plugins[p.__name__] = p
#
#    for p in plugins.values():
#        p.register()  
   
        
class BaublePlugin(object):
    
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
#    editors = []
#    views = []
    tools = []
    depends = []
    cmds = {}

    @classmethod
    def __init__(cls):        
        pass
    
    @classmethod
    def init(cls):
        '''
        init is run when Bauble is first started
        '''
        pass

    
    @classmethod
    def start(cls):
        '''
        start is run after the connection to the database has been made
        and after the interface is created but before it is shown
        it is the last think run before gtk.main() starts to loop
        '''

    @classmethod
    def register(cls):
        _register(cls)
    
    # NOTE: maybe create_tables should be a plugin method or a method
    # global to this module that way we can create things in order depending
    # on the plugin dependencies
    @classmethod
    def create_tables(cls):
        '''
        create the tables associated with this plugin
        '''
        for t in cls.tables:
            log.info("creating table " + t.__name__)
            t.dropTable(ifExists=True, cascade=True)            
            t.createTable()
    
    @staticmethod
    def default_filenames():
        '''
        return the list of filenames to get the default data set from
        the filenames should be of the form TableClass.txt
        '''
        return []
        
    
# TODO: is the code from here down still relevant???

class BaubleEditor(object):
    pass

        
class BaubleView(gtk.VBox):
    
    def __init__(self, *args, **kwargs):
        super(BaubleView, self).__init__(self, *args, **kwargs)


class BaubleTool(object):
    category = None
    label = None
    enabled = True
    @classmethod
    def start(cls):
        pass

    

    
