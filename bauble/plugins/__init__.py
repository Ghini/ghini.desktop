
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

#accessions = MultipleJoin('Accessions', joinColumn='plantname_id')
#joins = {'accessions': (table.Plantname, table.Accession, 'plantname_id')}

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

import os, sys, traceback
import gtk
from sqlobject import SQLObject, sqlmeta
import bauble.utils as utils

class plugins(object):
        
    class attrdict(dict):
        def __getattr__(self, attr):
            return self[attr]
            
    _plugins = {}    
    tables = attrdict()
    editors = attrdict()
    views = []
    tools = []

    def has_plugin(cls, item):
        return cls._plugins.has_key(item)
    has_plugin = classmethod(has_plugin)
        
        
    def __contains__(cls, item):
        return cls._plugins.has_key(item)
    __contains__ = classmethod(__contains__)
    
    # FIXME: why doesn't this work as a standard classmethod, i 
    # have to explicitly call __iter__()
    def __iter__(cls):
        print "plugins.__iter__"
        return iter(cls._plugins.values())
    __iter__ = classmethod(__iter__)


    def __init__(cls):
        print "plugins.__init__()"
        pass
    __init__ = classmethod(__init__)
    
    
    def init(cls):
        """
        call __init__() on all the plugins
        """
        print "plugins.init()"
        for p in cls._plugins.values():
            p.init()
    init = classmethod(init)

        
    
    def _register(cls, plugin_class):
        
        # check dependencies
        plugin_name = plugin_class.__name__
        print "registering ", plugin_name
        for dependency in plugin_class.depends:            
            #print 'depends: ', dependency
            if dependency not in cls._plugins:
                msg = "Can't load plugin %s. This plugin depends on %s but "\
                      "%s doesn't exist" %(plugin_name, dependency, dependency)
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                return
        cls._plugins[plugin_name] = plugin_class
        
        # add tables
        for t in plugin_class.tables:
            #print 'adding table: ', t.__name__            
            cls.tables[t.__name__] = t
        
        # add editors
        for e in plugin_class.editors:
            cls.editors[e.name] = e
        
        # add views and tools
        cls.views += plugin_class.views
        cls.tools += plugin_class.tools
        
    _register = classmethod(_register)

    def load(cls):
        # accumulate all the plugins in the module, call the register methods
        # once the plugins have been found
        plugins = cls._find_plugins()
        for p in plugins:
            cls._plugins[p.__name__] = p
        #print plugins
        for p in plugins:
            p.register()        
    load = classmethod(load)

    def _find_plugins():
        modules = []
        path, name = os.path.split(__file__)
        if path.find("library.zip") != -1: # using py2exe
            pkg = "views"
            zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
            x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
            s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
            rx = re.compile(s.encode('string_escape'))
            for filename in x:
                m = rx.match(filename)
                if m is not None:
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
                t, v, tb = sys.exc_info()
                msg = "** Error: could not import module %s\n\n%s" % \
                    (m, traceback.format_exc())
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                continue
            if hasattr(mod, "plugin"):                 
                plugins.append(mod.plugin)
        return plugins
        
    _find_plugins = staticmethod(_find_plugins)
    
    
    def init2(cls):
        print 'Plugins._init'
        try:
            if cls._initialized == True:
                print 'already initialized'
                return                
        except AttributeError, e:
             pass
        #if cls._initialized: return
        cls._initialized = True
        print 'initialized is True'
        modules = []
        path, name = os.path.split(__file__)
        if path.find("library.zip") != -1: # using py2exe
            pkg = "views"
            zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
            x = [zipfiles[file][0] for file in zipfiles.keys() if pkg in file]
            s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
            rx = re.compile(s.encode('string_escape'))
            for filename in x:
                m = rx.match(filename)
                if m is not None:
                    modules.append('%s.%s' % (pkg, m.group(1)))
        else:                
            for d in os.listdir(path):
                full = path + os.sep + d                
                if os.path.isdir(full) and os.path.exists(full + os.sep + "__init__.py"):
                    #modules.append("plugins." + d)
                    modules.append(d)

        for m in modules:
            print "importing " + m
            #mod = __import__(m, globals(), locals(), ['plugins'])
            try:
                mod = __import__(m, globals(), locals(), ['plugins'])
            except Exception, e:
                t, v, tb = sys.exc_info()
                msg = "** Error: could not import module %s\n\n%s" % \
                    (m, traceback.format_exc())
                utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                continue
            if hasattr(mod, "plugin"): 
                p = mod.plugin()  
                #print p.__class__.__name__
                cls._plugins[p.__class__.__name__] = p
                #cls._plugins[p.__name__]
                #cls._plugins.append(p)
                        
        bad_plugins = []
        for plugin_name, plugin in cls._plugins.iteritems():
            # TODO: check the plugin dependencies, if the dependencies don't exist
            # then remove the plugin from the list and show a message, else
            # add the table, editors, etc to this class
            print 'plugin: ' + plugin_name
            for dependency in plugin.depends:
                print 'depends: ', dependency
                if dependency not in cls._plugins:
                    msg = "Can't load plugin %s. This plugin depends on %s but "\
                          "%s doesn't exist" %(plugin_name, dependency, dependency)
                    utils.message_dialog(msg, gtk.MESSAGE_ERROR)
                    bad_plugins.append(plugin_name)
                    #cls._plugins.pop(plugin_name)
            
        # pop those plugins whose dependencies couldn't be met
        for p in bad_plugins:
            cls._plugins.pop(p)
            
        # NOTE: views can depend on tables so add tables first
        for plugin_name, plugin in cls._plugins.iteritems():            
            for t in plugin.tables:
                print 'adding table: ', t.__name__            
                cls.tables[t.__name__] = t
                
        #for plugin_name, plugin in cls._plugins.iteritems():                    
            print 'adding everything else for ', plugin_name
            for e in plugin.editors:
                cls.editors[e.name] = e
            cls.views += plugin.views
            cls.tools += plugin.tools
            
        # now that all the meta is in the plugins registry, let's  
                        
    
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

    def __init__(cls):
        pass
    __init__ = classmethod(__init__)
    
    def init(cls):
        pass
    init = classmethod(init)

    def register(cls):
        plugins._register(cls)
    register = classmethod(register)
    
    def create_tables(cls):
        for t in cls.tables:
            print "creating table ", t.__name__
            t.dropTable(ifExists=True, cascade=True)            
            t.createTable()
    create_tables = classmethod(create_tables)


class BaubleTable(SQLObject):        
    sqlmeta.cacheValues = False
    
    def __init__(self, **kw):
        super(BaubleTable, self).__init__(**kw)
        self.values = {}

    
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
    
    def start(cls):
        pass
    start = classmethod(start)
    
plugins()
#plugins.init()
    
