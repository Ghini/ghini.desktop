import os
import sys
import tempfile

import gtk
from sqlalchemy import *
from sqlalchemy.orm import *
from mako.template import Template

import bauble
from bauble.utils.log import debug
import bauble.utils as utils
import bauble.utils.desktop as desktop
import bauble.paths as paths
from bauble.plugins.plants.species import Species
from bauble.plugins.garden.plant import Plant
from bauble.plugins.garden.accession import Accession
from bauble.plugins.abcd import create_abcd, ABCDAdapter, ABCDElement
from bauble.plugins.report import get_all_plants, get_all_species, \
     get_all_accessions, FormatterPlugin, SettingsBox


class TemplateFormatterSettingsBox(SettingsBox):

    def __init__(self, report_dialog=None, *args):
        super(TemplateFormatterSettingsBox, self).__init__(*args)
        self.widgets = utils.GladeWidgets(os.path.join(paths.lib_dir(),
                               "plugins", "report", 'template', 'gui.glade'))
        # keep a refefence to settings box so it doesn't get destroyed in
        # remove_parent()
        settings_box = self.widgets.settings_box
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(settings_box)
        #self.presenter = SettingsBoxPresenter(self.widgets)

    def get_settings(self):
        """
        """
        return {'template': self.widgets.template_chooser.get_filename(),
                'private': self.widgets.private_check.get_active()}

    def update(self, settings):
        if 'template' in settings and settings['template']:
            self.widgets.template_chooser.\
                                        set_filename(settings['template'])
        if 'private' in settings:
            self.widgets.private_check.set_active(settings['private'])


class TemplateFormatterPlugin(FormatterPlugin):

    title = _('Template')

    @staticmethod
    def get_settings_box():
        return TemplateFormatterSettingsBox()


    @staticmethod
    def format(objs, **kwargs):
        template_filename = kwargs['template']
        use_private = kwargs.get('private', True)
        if not template_filename:
            msg = _('Please selecte a template.')
            utils.message_dialog(error_msg, gtk.MESSAGE_WARNING)
            return False
        template = Template(filename=template_filename)

        # TODO: provide the option to get the objects as either plants
        # or directly as they appear in the search results
        plants = get_all_plants(objs)
        report = template.render(plants=plants)
        # assume the template is the same file type as the output file
        head, ext = os.path.splitext(template_filename)
        fd, filename = tempfile.mkstemp(suffix=ext)
        os.write(fd, report)
        os.close(fd)
        try:
            desktop.open(filename)
        except OSError:
            utils.message_dialog(_('Could not open the report with the '\
                                   'default program. You can open the '\
                                   'file manually at %s') % filename)
        return report


formatter_plugin = TemplateFormatterPlugin

