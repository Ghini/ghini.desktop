

import os, sys

class Singleton(object):
        _instance = None
        def __new__(cls, *args, **kwargs):
            if not cls._instance:
                cls._instance = super(Singleton, cls).__new__(
                                   cls, *args, **kwargs)
            return cls._instance
            
            
class _Plugins:#(Singleton):
    
    tables = []
    editors = []
    views = []
    plugins = []
            
    def __init__(cls):
        print 'Plugins._init'
        #print cls._initialized
        #if cls._initialized: return
        #cls._initialized = True
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
                #self[p.label] = p
                # get editors, views, tables, dependencies, etc..
                #cls.modules[mod.view] = m
                print cls.plugins
                cls.plugins += p
                cls.tables += p.tables
                cls.editors += p.editors
                cls.views += p.views
    #init = classmethod(init)
    
Plugins = _Plugins()
#Plugins.init()