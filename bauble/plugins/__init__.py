#
# plugin module
#

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

# TODO: need a way to add tables to the database base without creating a new
# database completely, in case someone drops in a plugin we can create the 
# needed tables

# TODO: if a plugin is removed then a dialog should be popped
# up to ask if you want to remove the joins

import os, sys, traceback, re
import gtk
from sqlalchemy import *
import bauble
import bauble.utils as utils
from bauble.utils.log import log, debug
from bauble.i18n import *

plugins = {}
views = {}
tools = {}
editors = {}
tables = {}

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
    
    # add tables
    for t in plugin_class.tables:
        # TODO: this isn't really necessary anymore
#        if not issubclass(t, BaubleTable):
#            raise TypeError('%s table from plugin %s is not an instance of '\
#                            'BaubleTable' % (t, plugin_name))
        tables[t.__name__] = t
    
    # add editors
    for e in plugin_class.editors:
        if not issubclass(e, BaubleEditor):
            raise TypeError(_('%(editor)s editor from plugin %(plugin)s is not '\
                              'an instance of BaubleEditor') % \
                              {'editor': e, 'plugin': plugin_name})
        editors[e.__name__] = e
    
    # add views
    for v in plugin_class.views:
        if not issubclass(v, BaubleView):
            raise TypeError(_('%(view)s view from plugin %(plugin)s is not '\
                              'an instance of BaubleView') % \
                              {'view': v, 'plugin': plugin_name})
        views[v.__name__] = v
    
    # add tools
    for l in plugin_class.tools:    
        if not issubclass(l, BaubleTool):
            raise TypeError(_('%(tool)s tool from plugin %(plugin)s is not an '\
                            'instance of BaubleTool') % \
                            {'tool': l, 'plugin': plugin_name})
        tools[l.__name__] = l


def _find_plugin_names():
    modules = []
    path, name = os.path.split(__file__)
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
            full = path + os.sep + d
            if os.path.isdir(full) and os.path.exists(os.path.join(full, "__init__.py")):
                modules.append(d)
    return modules

#def _find_plugin_modules():
#    import imp
#    modules = []
#    path, name = os.path.split(__file__)
#    if path.find("library.zip") != -1: # using py2exe
#        pkg = "bauble.plugins"
#        zipfiles = __import__(pkg, globals(), locals(), [pkg]).__loader__._files 
##        for f in zipfiles.keys():
##            pass
#
#        x = [zipfiles[file][0] for file in zipfiles.keys() \
#         if "bauble\\plugins" in file]
#        s = '.+?' + os.sep + pkg + os.sep + '(.+?)' + os.sep + '__init__.py[oc]'
#        rx = re.compile(s.encode('string_escape'))        
#        for filename in x:    
#            m = rx.match(filename)
#            if m is not None:
#                modules.append('%s.%s' % (pkg, m.group(1)))
#                
#    else:                
#        for d in os.listdir(path):        
#            full = path + os.sep + d                
#            if os.path.isdir(full) and os.path.exists(full + 
#                              os.sep + "__init__.py"):
#                modules.append(d)
#                
#    found = []
#    for m in modules:
#        mod = __import__(m, globals(), locals(), ['plugins'])
#        #if mod is not None:
#        found.append(mod)
#    return found


def _find_plugins():
    plugin_names = _find_plugin_names()
                
    # import the modules and test if they provide a plugin to make sure 
    # they are plugin modules
    plugins = []
    for name in plugin_names:
        try:
            mod = __import__(name, globals(), locals(), ['plugins'])
        except Exception, e:
            msg = _("Could not import the %s module.") % name
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
    cmds = []

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

    

    
