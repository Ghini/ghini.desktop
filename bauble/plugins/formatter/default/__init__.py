# 
# the default formatter module
#

import sys, os
import gtk
import bauble.utils as utils
from bauble.utils.log import debug
import bauble.paths as paths

# TODO: there's two ways to handle this settings box business, we can either
# request the settings box from the plugin or we can pass the widget
# to the plugin that the box is to be added to

class SettingsBoxPresenter:
    
    def __init__(self, widgets):
        self.widget = widgets



class SettingsBox(gtk.VBox):
    
    def __init__(self, *args):
        super(SettingsBox, self).__init__(*args)
        # TODO: should somehow find where this is installed
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(), 
                               "plugins", "formatter", 'default', 'gui.glade'))
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(self.widgets.settings_box)
        presenter = SettingsBoxPresenter(self.widgets)
        
        
    def get_settings(self):
        '''
        return a dict of settings from the settings box gui        
        '''
        return {'stylesheet': self.widgets.stylesheet_chooser.get_filename(),
                'renderer': self.widgets.renderer_combo.get_active_text()}
        
    
    def update(self, settings={}):
        debug('SettingsBox.update(%s)' % settings)
        try:
            self.widgets.stylesheet_chooser.set_filename(settings['stylesheet'])
            utils.combo_set_active_text(self.widgets.renderer_combo, 
                                        settings['renderer'])
        except KeyError, e:
            #debug('SettingsBox.update(): KeyError -- %s' % e)
            pass
        except Exception, e:
            #debug('SettingsBox.update(): Exception -- %s' % e)
            #debug(e)
            pass


#class FormatterSettings(object):
#    
#    _box = None    
#    
#    @classmethod
#    def get_box(cls):
#        if cls._box is None:            
#            cls._box = SettingsBox()
#        return cls._box
#    
#    @classmethod
#    def update(cls, settings={}):
#        print settings
        
        
class FormatterPlugin(object):
    #settings_box = SettingsBox()
    title = 'Default'
    
    _settings_box = None
    
    @classmethod
    def get_settings_box(cls):
        #if cls._settings_box is None:
        #    cls._settings_box = SettingsBox()
        #return cls._settings_box
        return SettingsBox()    
    
#    def _get_settings_box(cls):
#        if cls._settings_box is None:
#            cls._settings_box = SettingsBox()
#        return cls._settings_box
#    settings_box = property(_get_settings_box)    
    
    @classmethod
    def format(cls, objs, **kwargs):
        debug('format(%s)' % kwargs)
        for obj in objs:
            debug(obj)
    format = format
    
formatter = FormatterPlugin

# SettingsBox shouldn't be an instance

    
#class Formatter:
#    
#    
#    
#    @staticmethod    
#    def format(objs, **kwargs):
#        pass
#    
#formatter = Formatter
#title = 'Default'
#
#def format(objs, **kwargs):
#    pass
#
#if sys.platform == "win32":
#    fop_cmd = 'fop.bat'
#else:
#    fop_cmd = 'fop'
#    
#renderers_map = {'Apache FOP': fop_cmd + \
#                 ' -fo %(fo_filename)s -pdf %(out_filename)s',
#                 'XEP': 'xep -fo %(fo_filename)s -pdf %(out_filename)s',
##                 'xmlroff': 'xmlroff -o %(out_filename)s %(fo_filename)s',
##                 'Ibex for Java': 'java -cp /home/brett/bin/ibex-3.9.7.jar \
##         ibex.Run -xml %(fo_filename)s -pdf %(out_filename)s'
#                }
#
#
#class SettingsBoxPresenter(object):
#    
#    def __init__(self, view):
#        self.view = view
#        
#    def get_settings(self):
#        '''
#        return widget values
#        '''
#    
#
#class SettingsBox(gtk.VBox):
#    
#    def __init__(self, *args):
#        super(SettingsBox, self).__init__(*args)
#        presenter = SettingsBoxPresenter()
#        
#        
#    def get_settings(self):
#        '''
#        return a dict of settings that can be passed to format
#        '''
#        {}
#
#def init_settings_box():
#    box = gtk.VBox()
#    expander = gtk.Expander('Renderer')
#    combo = gtk.ComboBox()
#    
#    box.pack_start(expander)
#    
#    
#class DFOPresenter(object):
#    pass
#
#class DefaultFormatterOptions(object):
#    pass
#
#settings_box = SettingsBox()