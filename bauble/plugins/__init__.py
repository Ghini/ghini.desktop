
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

print 'import plugins'

import os    
import gtk
import os, sys
from sqlobject import SQLObject, sqlmeta

    
class BaublePlugin(object):
    
    tables = []
    editors = []
    views = []
    tools = []


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
    pass


class plugins:
    
    
    class attrdict(dict):
        def __getattr__(self, attr):
            return self[attr]
            
    _plugins = {}
    tables = attrdict()
    editors = attrdict()
    #views = attrdict()
    views = []
    tools = []

    def init(cls):
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
            mod = __import__(m, globals(), locals(), ['plugins'])
            if hasattr(mod, "plugin"): 
                p = mod.plugin()  
                #print p.__class__.__name__
                cls._plugins[p.__class__.__name__] = p
                #cls._plugins[p.__name__]
                #cls._plugins.append(p)
                        
        for plugin in cls._plugins.value():
            # TODO: check the plugin dependencies, if the dependencies don't exist
            # then remove the plugin from the list and show a message, else
            # add the table, editors, etc to this class
            
                for t in p.tables:
                    #print '** adding ' + t.name
                    #print t.__name__
                    cls.tables[t.__name__] = t
                for e in p.editors:
                    cls.editors[e.name] = e
                cls.views += p.views
                cls.tools += p.tools
                
            # TODO: now that we have all the plugins loaded we need to check their
            # dependencies and 
                #for v in p.views:
                #    cls.tables[v.name] = v
                #cls.tables += p.tables
                #cls.editors += p.editors
                #
    init = classmethod(init)


plugins.init()
    
