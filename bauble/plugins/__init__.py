
# plugins, tables, editors and views should inherit from
# the appropriate classes

# TODO: need to consider 
# first initialization so we know whether to add joins to table, this 
# might mean we have to keep a cache of what has been initialized and what
# hasn't, or possibly just create a .initialized file in the module 
# directory to indicate that the plugin has been intialized, though this 
# means we would have to have write permission to the plugin directory 
# which could be problematic, a file with a list of initialized plugins 
# would be best i reckon and then we can just grep the file for the plugin
# name

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
import bauble
import bauble.utils as utils
from bauble.utils.log import log, debug
from sqlobject import SQLObject, sqlmeta, DateTimeCol
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
    
    
def start_plugins():
    '''
    start of the plugins
    '''
    for p in plugins.values():
        p.start()
        
        
def _register(plugin_class):        
    # check dependencies
    plugin_name = plugin_class.__name__
    if not bauble.main_is_frozen():
	log.info("registering " + plugin_name)
    for dependency in plugin_class.depends:            
        if dependency not in plugins:
            msg = "Can't load plugin %s. This plugin depends on %s but "\
                  "%s doesn't exist" %(plugin_name, dependency, dependency)
            utils.message_dialog(msg, gtk.MESSAGE_ERROR)
            plugins.pop(plugin_name)
            return
                    
    plugins[plugin_name] = plugin_class
    
    # add tables
    for t in plugin_class.tables:
        if not issubclass(t, BaubleTable):
            raise TypeError('%s table from plugin %s is not an instance of '\
                            'BaubleTable' % (t, plugin_name))
        tables[t.__name__] = t
    
    # add editors
    for e in plugin_class.editors:
        if not issubclass(e, BaubleEditor):
            raise TypeError('%s table from plugin %s is not an instance of '\
                            'BaubleEditor' % (e, plugin_name))
        editors[e.__name__] = e
    
    # add views
    for v in plugin_class.views:
        if not issubclass(v, BaubleView):
            raise TypeError('%s table from plugin %s is not an instance of '\
                            'BaubleView' % (v, plugin_name))        
        views[v.__name__] = v
    
    # add tools
    for l in plugin_class.tools:    
        if not issubclass(l, BaubleTool):
            raise TypeError('%s table from plugin %s is not an instance of '\
                            'BaubleTool' % (l, plugin_name))                
        tools[l.__name__] = l


def _find_plugins():
    modules = []
    path, name = os.path.split(__file__)
    if path.find("library.zip") != -1: # using py2exe
        pkg = "bauble.plugins"
        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
#        for f in zipfiles.keys():
#            pass

        x = [zipfiles[file][0] for file in zipfiles.keys() \
	     if "bauble\\plugins" in file]
        s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
        rx = re.compile(s.encode('string_escape'))        
        for filename in x:    
            m = rx.match(filename)
            if m is not None:
                modules.append('%s.%s' % (pkg, m.group(1)))
                
    else:                
        # TODO: revert this back to make all plugins load
        #for d in 'plants':                            
        for d in os.listdir(path):        
            full = path + os.sep + d                
            if os.path.isdir(full) and os.path.exists(full + 
						      os.sep + "__init__.py"):
                modules.append(d)
                
    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    for m in modules:
        try:
            mod = __import__(m, globals(), locals(), ['plugins'])
        except Exception, e:
            msg = "Could not import the %s module." % m#\n\n%s" % 
            utils.message_details_dialog(msg, str(traceback.format_exc()), 
					 gtk.MESSAGE_ERROR)
	    raise
            #continue
        if hasattr(mod, "plugin"):                 
            plugins.append(mod.plugin)
    return plugins


def load():
    # accumulate all the plugins in the module, call the register methods
    # once the plugins have been found, this is called at the bottom of 
    # this file
    found = _find_plugins()
    for p in found:                
        plugins[p.__name__] = p

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
        for t in cls.tables:
            log.info("creating table " + t.__name__)
            t.dropTable(ifExists=True, cascade=True)            
            t.createTable()
        
        
#from sqlalchemy import *
#class BaubleTable(object):
#    
#    def __init__(self, table):
#        debug(self.__class__)
#        self.mapper = mapper(self.__class__, table)
#    
#    class sqlmeta:
#        pass
#        
#    def markup(self):
#        return str(self)

    
class BaubleTable(SQLObject):
       
    def __init__(self, **kw):        
        super(BaubleTable, self).__init__(**kw)        
        self.values = {}
        
    def markup(self):
        return str(self)
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

        
class BaubleView(gtk.VBox):
    
    def __init__(self, *args, **kwargs):
        super(BaubleView, self).__init__(self, *args, **kwargs)
        #self.set_label('')
        #self.set_shadow_type(gtk.SHADOW_NONE)


class BaubleTool(object):
    category = None
    label = None
    enabled = True
    @classmethod
    def start(cls):
        pass

    
#def init_module():
#    load()
#init_module()
load()
    
