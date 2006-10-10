# 
# the default formatter module
#

import sys, os, tempfile, traceback
import gtk
from sqlalchemy import *
import bauble.utils as utils
from bauble.utils.log import debug
import bauble.paths as paths
import bauble.plugins.formatter as format_plugin
import bauble.plugins.abcd as abcd
from bauble.plugins.garden.plant import Plant, plant_table
from bauble.plugins.garden.accession import accession_table



# TODO: there's two ways to handle this settings box business, we can either
# request the settings box from the plugin or we can pass the widget
# to the plugin that the box is to be added to

# TODO: if formatter chosen has any problems, i.e. the stylesheet file doesn't
# exis,  it would be good to desensitize the ok button and show a message in
# the status bar or something, then again we could wait until Ok is pressed 
# until we check for errors since we can't check if the fo renderer doesn't 
# exist

# TODO: need to do something about errors and showing them to the user, e.g
# if the stylesheet is invalid then currently there is nothing telling the user
# that this is so

# TODO: look for this on the path before starting anything and warn the use
# so they have a clue why the formatter isn't working

if sys.platform == "win32":
    fop_cmd = 'fop.bat'
else:
    fop_cmd = 'fop'
    
    
# TODO: support FOray, see http://www.foray.org/
renderers_map = {'Apache FOP': fop_cmd + \
                               ' -fo %(fo_filename)s -pdf %(out_filename)s',
                 'XEP': 'xep -fo %(fo_filename)s -pdf %(out_filename)s',
#                 'xmlroff': 'xmlroff -o %(out_filename)s %(fo_filename)s',
#                 'Ibex for Java': 'java -cp /home/brett/bin/ibex-3.9.7.jar \
#         ibex.Run -xml %(fo_filename)s -pdf %(out_filename)s'
                }

class SettingsBoxPresenter:
    
    def __init__(self, widgets):
        self.widgets = widgets
        model = gtk.ListStore(str)
        for name in renderers_map:
            model.append([name])            
        self.widgets.renderer_combo.set_model(model)

    

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
                'renderer': self.widgets.renderer_combo.get_active_text(),
                'authors': self.widgets.author_check.get_active()}
        
    
    def update(self, settings={}):
#        debug('SettingsBox.update(%s)' % settings)
        try:
            self.widgets.stylesheet_chooser.set_filename(settings['stylesheet'])
            utils.combo_set_active_text(self.widgets.renderer_combo, 
                                        settings['renderer'])
            self.widgets.author_check.set_active(settings['authors'])
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
    
    title = 'Default'
    
    @classmethod
    def get_settings_box(cls):
        # TODO: can we somehow make this static so we don't have to recreate
        # it everytime, the main problem with this is guess is that the widgets
        # get destroyed when there aren't any more references to them
        #if cls._settings_box is None:
        #    cls._settings_box = SettingsBox()
        #return cls._settings_box
        return SettingsBox()    

    
    @classmethod
    def format(cls, objs, **kwargs):
#        debug('format(%s)' % kwargs)
        stylesheet = kwargs['stylesheet']
        authors = kwargs['authors']
        fo_cmd = renderers_map[kwargs['renderer']]
        
        plants = format_plugin.get_all_plants(objs)
        if len(plants) == 0:
            utils.message_dialog('There are no plants in the search results.  '\
                                 'Please try another search.')
            return
        
        abcd_data = abcd.plants_to_abcd(plants, authors=authors)                
        
        # this adds a "distribution" tag from the species meta, we
        # use this when generating labels but it should be able to be safely 
        # ignored since it's not in the ABCD namespace
        for el in abcd_data.getiterator(tag='{http://www.tdwg.org/schemas/abcd/2.06}Unit'):
            unit_id = el.xpath('abcd:UnitID', 
                               {'abcd': 'http://www.tdwg.org/schemas/abcd/2.06'})
            divider = '.' # TODO: should get this from the prefs or bauble meta
            acc_code, plant_code = unit_id[0].text.rsplit(divider, 1)
            acc_id = select([accession_table.c.id], accession_table.c.code==acc_code).scalar()
            plant_id = select([plant_table.c.id], plant_table.c.accession_id==acc_id).scalar()
            session = create_session()
            plant = session.get(Plant, plant_id)
            meta = plant.accession.species.species_meta
            if meta is not None:
                dist = meta.distribution
                if dist is not None:
                    etree.SubElement(el, 'distribution').text = dist                                        
            session.close()    
            
#        debug(etree.dump(abcd_data.getroot()))

        # create xsl fo file
        dummy, fo_filename = tempfile.mkstemp()
        style_etree = etree.parse(stylesheet)
        transform = etree.XSLT(style_etree)
        
        result = transform(abcd_data)
        fo_outfile = open(fo_filename, 'w')
        fo_outfile.write(unicode(result))
        fo_outfile.close()
        
        dummy, filename = tempfile.mkstemp()                
        filename = '%s.pdf' % filename
        
        # run the formatter to produce the pdf file, the command has to be
        # on the path for this to work
        fo_cmd = fo_cmd % ({'fo_filename': fo_filename, 
                            'out_filename': filename})
        os.system(fo_cmd)        
        
        utils.startfile(filename)
        

# expose the formatter
try:
    import lxml.etree as etree
except ImportError: 
    utils.message_dialog('The <i>lxml</i> package is required for the default '\
                         'formatter plugins')        
else:
    formatter = FormatterPlugin