
# plugins, tables, editors and views should inherit from
# the appropriate classes

# TODO: how do we access tables should it be 
# plugins[plugin_name].tables[table_name], that's pretty long
# or access all tables like plugins.tables[table_name] and be able 
# to retrieve the module name from the table

# TODO: need to consider 
# first initialization so we know whether to add joins to table, this 
# might mean we have to keep a cache of what has been initialized and what
# hasn't, or possibly just create a .initialized file in the module 
# directory to indicate that the plugin has been intialized, though this 
# means we would have to have write permission to the plugin directory 
# which could be problematic, a file with a list of initialized plugins 
# would be best i reckon and then we can just grep the file for the plugin
# name

# TODO: what about tools, should they be separate or a plugin, i think
# a plugin should be fine, what differentiates a tool from a plugin
# other than the tools menu, as long as the plugin defines a tools
# list for what tools it provides then that should be enough, should
# also consider a tools_category so we cant create a rational menu
# layout for tools

# TODO: we could just have a provides=[] list instead of a different
# list for each of tables, editors, blah, blah, then we could just
# test the parent class of what it provides to know what to do with 
# it, this might be getting too abstract, and since we will want to
# access thing like plugins.tables[table_name] then stick with 
# module level list of tables may make more sense

# TODO: a plugin cannot change a table but can add joins to a table not
# in its plugin module  throught the sqlmeta.addJoin method

# TODO: need a way to add tables to the database base without creating a new
# database completely, see sqlobject-admin, this also means to we need
# a way to know whether this is the first time this plugin has been loaded

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

import os, sys, traceback, re
import gtk
import bauble.utils as utils
from bauble.utils.log import log, debug
from sqlobject import SQLObject, sqlmeta, DateTimeCol, StringCol
#from sqlobject.inheritance import InheritableSQLObject
from datetime import datetime

plugins = {}
views = {}
tools = {}
editors = {}
tables = {}

            
def init_plugins():
    """
    initialized all the plugins in plugins
    """    
    for p in plugins.values():
        p.init()
    
    
def _register(plugin_class):
        
    # check dependencies
    plugin_name = plugin_class.__name__
    log.info("registering " + plugin_name)
    for dependency in plugin_class.depends:            
        #print 'depends: ', dependency
        if dependency not in plugins:
            msg = "Can't load plugin %s. This plugin depends on %s but "\
                  "%s doesn't exist" %(plugin_name, dependency, dependency)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            plugins.pop(plugin_name)
            return
                    
    plugins[plugin_name] = plugin_class
    
    # add tables
    for t in plugin_class.tables:
        #print 'adding table: ', t.__name__            
        tables[t.__name__] = t
    
    # add editors
    for e in plugin_class.editors:
        editors[e.__name__] = e
    
    # add views
    for v in plugin_class.views:
        views[v.__name__] = v
    
    # add tools
    for t in plugin_class.tools:    
        tools[t.__name__] = t


def _find_plugins():
    modules = []
    path, name = os.path.split(__file__)
    if path.find("library.zip") != -1: # using py2exe
        debug("library.zip")
        pkg = "bauble.plugins"
        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
        #debug(zipfiles)
        for f in zipfiles.keys():
            pass
            #debug(f)
        #return ()
        #x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
        x = [zipfiles[file][0] for file in zipfiles.keys() if "bauble\\plugins" in file]
        debug(x)
        s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
        rx = re.compile(s.encode('string_escape'))        
        for filename in x:    
            debug(filename)
            m = rx.match(filename)
            if m is not None:
                debug('%s.%s' % (pkg, m.group(1)))
                modules.append('%s.%s' % (pkg, m.group(1)))
                
    else:                
        for d in os.listdir(path):
            full = path + os.sep + d                
            if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                #modules.append("plugins." + d)
                modules.append(d)
                
    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    for m in modules:
        try:
            mod = __import__(m, globals(), locals(), ['plugins'])
        except Exception, e:
            msg = "Could not import the %s module." % m#\n\n%s" % 
            utils.message_details_dialog(msg, str(traceback.format_exc()), gtk.MESSAGE_ERROR)
            continue
        if hasattr(mod, "plugin"):                 
            plugins.append(mod.plugin)
    return plugins


def load():
    # accumulate all the plugins in the module, call the register methods
    # once the plugins have been found
    found = _find_plugins()
    for p in found:        
        plugins[p.__name__] = p
    #print plugins
    for p in plugins.values():
        p.register()  


# TODO: use this as the metaclass for BaublePlugin to automatically make
# any methods called init() to be classmethods
class BaublePluginMeta(object):
    
    def __init__(self):
        """
        should use this as 
        """
        pass
        
        
class BaublePlugin(object):
    tables = []
    editors = []
    views = []
    tools = []
    depends = []

    @classmethod
    def __init__(cls):
        pass
    
    @classmethod
    def init(cls):
        pass

    @classmethod
    def register(cls):
        _register(cls)
    
    # NOTE: maybe create_tables should be a plugin method or a method
    # global to this module that way we can create things in order depending
    # on the plugin dependencies
    @classmethod
    def create_tables(cls):
        for t in cls.tables:
            log.info("creating table " + t.__name__)
            t.dropTable(ifExists=True, cascade=True)            
            t.createTable()
        
        
class BaubleTable(SQLObject):
    sqlmeta.cacheValues = False
    
    def __init__(self, **kw):        
        super(BaubleTable, self).__init__(**kw)        
        self.values = {}
        
### i can't get this to work, i don't understand
#    """
#    This is the part to enable automatic updating of changed objects
#    """
#    _created = DateTimeCol(default=datetime.now(), dbName='_created')
#    _updated = DateTimeCol(default=datetime.now(), dbName='_updated')
#    def _SO_setValue(self, name, value, from_python, to_python):
#        debug(name)
#        if name == '_updated' :
#            debug('_updating')
#            SQLObject._SO_setValue(self, name, value, from_python, to_python)            
#        else :
#            self.set(**{name: value, '_updated' : datetime.now()})                

    #values = {}
    #@classmethod
    #def _get_values
    
class BaubleEditor(object):
    pass

        
class BaubleView(gtk.Frame):
    
    def __init__(self, *args, **kwargs):
        super(BaubleView, self).__init__(self, *args, **kwargs)
        self.set_label('')
        self.set_shadow_type(gtk.SHADOW_NONE)


class BaubleTool(object):
    category = None
    label = None

    @classmethod
    def start(cls):
        pass

    
def init_module():
    load()
init_module()
    
