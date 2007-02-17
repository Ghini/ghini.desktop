# 
# the default report module
#

import sys, os, tempfile, traceback
import gtk
from sqlalchemy import *
import bauble
from bauble.utils.log import debug
#debug('1: %s' % bauble)
import bauble.utils as utils
#debug('2: %s' % bauble)
#debug('3: %s' % bauble)
import bauble.paths as paths
debug('4: %s' % bauble)
from bauble.plugins.garden.plant import Plant, plant_table
debug('5: %s' % bauble)
from bauble.plugins.garden.accession import accession_table
debug('6: %s' % bauble)

#import bauble.plugins.abcd as abcd
from bauble.plugins.abcd import plants_to_abcd
debug('7: %s' % bauble)

# i don't understand why import bauble.plugins.report as report doesn't work,
# it probably has something to do with the fact that we import the plugins 

#import bauble.plugins.report as report_plugin
from bauble.plugins.report import get_all_plants, FormatterPlugin, SettingsBox

# TODO: look for renderers on the path before starting anything and warn the use
# so they have a clue why the formatter isn't working
# No PDF renders installed. For a free renderer download Apache FOP at 
# http://... If you do have a PDF renderer installed make sure it is on the path.
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


#class DefaultFormatterSettingsBox(report.SettingsBox):
class DefaultFormatterSettingsBox(SettingsBox):
    
    def __init__(self, report_dialog=None, *args):
        super(DefaultFormatterSettingsBox, self).__init__(*args)
        # TODO: should somehow find where this is installed
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(), 
                               "plugins", "report", 'default', 'gui.glade'))
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(self.widgets.settings_box)
        self.presenter = SettingsBoxPresenter(self.widgets)
        
        
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



_settings_box = DefaultFormatterSettingsBox()
class DefaultFormatterPlugin(FormatterPlugin):
    
    title = 'Default'
    
    @staticmethod
    def get_settings_box():
        return DefaultFormatterSettingsBox()    
    
    @staticmethod
    def format(objs, **kwargs):
#        debug('format(%s)' % kwargs)        
        stylesheet = kwargs['stylesheet']
        authors = kwargs['authors']
        renderer = kwargs['renderer']
        error_msg = None
        if not stylesheet:
            error_msg = 'Please select a stylesheet.'
        elif not renderer:        
            error_msg = 'Please select a a renderer'        
        if error_msg is not None:
            utils.message_dialog(error_msg, gtk.MESSAGE_WARNING)
            return False            
        
        fo_cmd = renderers_map[renderer]
        #plants = report_plugin.get_all_plants(objs)
        plants = get_all_plants(objs)
        if len(plants) == 0:
            utils.message_dialog('There are no plants in the search '
                                 'results.  Please try another search.')
            return False
        
        #abcd_data = abcd.plants_to_abcd(plants, authors=authors)
        abcd_data = plants_to_abcd(plants, authors=authors)
        
        # this adds a "distribution" tag from the species meta, we
        # use this when generating labels but it should be able to be safely 
        # ignored since it's not in the ABCD namespace
        for el in abcd_data.getiterator(tag='{http://www.tdwg.org/schemas/abcd/2.06}Unit'):
            unit_id = el.xpath('abcd:UnitID', 
                            {'abcd': 'http://www.tdwg.org/schemas/abcd/2.06'})
            divider = '.' # TODO: should get this from the prefs or bauble meta
            acc_code, plant_code = unit_id[0].text.rsplit(divider, 1)
            acc_id = select([accession_table.c.id],
                            accession_table.c.code==acc_code).scalar()
            plant_id = select([plant_table.c.id],
                              plant_table.c.accession_id==acc_id).scalar()
            session = create_session()
            plant = session.get(Plant, plant_id)

            # TODO: need to change this to use new species_distribution
##             meta = plant.accession.species.species_meta
##             if meta is not None:
##                 dist = meta.distribution
##                 if dist is not None:
##                     etree.SubElement(el, 'distribution').text = dist
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
        
        # run the report to produce the pdf file, the command has to be
        # on the path for this to work
        fo_cmd = fo_cmd % ({'fo_filename': fo_filename, 
                            'out_filename': filename})
        os.system(fo_cmd)        
        
        utils.startfile(filename)
        return True
        

# expose the formatter
try:
    import lxml.etree as etree
except ImportError: 
    utils.message_dialog('The <i>lxml</i> package is required for the '\
                         'default report plugins')        
else:
    formatter_plugin = DefaultFormatterPlugin
