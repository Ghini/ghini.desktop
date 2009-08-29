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


class MakoFormatterSettingsBox(SettingsBox):

    def __init__(self, report_dialog=None, *args):
        super(MakoFormatterSettingsBox, self).__init__(*args)
        self.widgets = utils.load_widgets(os.path.join(paths.lib_dir(),
                               "plugins", "report", 'mako', 'gui.glade'))
        # keep a refefence to settings box so it doesn't get destroyed in
        # remove_parent()
        self.settings_box = self.widgets.settings_box
        self.widgets.remove_parent(self.widgets.settings_box)
        self.pack_start(self.settings_box)


    def get_settings(self):
        """
        """
        return {'template': self.widgets.template_chooser.get_filename(),
                'private': self.widgets.private_check.get_active()}

    def update(self, settings):
        if 'template' in settings and settings['template']:
            self.widgets.template_chooser.set_filename(settings['template'])
        if 'private' in settings:
            self.widgets.private_check.set_active(settings['private'])


_settings_box = MakoFormatterSettingsBox()

class MakoFormatterPlugin(FormatterPlugin):
    """
    The MakoFormatterPlugins passes the values in the search
    results directly to a Mako template.  It is up to the template
    author to validate the type of the values and act accordingly if not.
    """

    title = _('Mako')

    @staticmethod
    def get_settings_box():
        return _settings_box


    @staticmethod
    def format(objs, **kwargs):
        template_filename = kwargs['template']
        use_private = kwargs.get('private', True)
        if not template_filename:
            msg = _('Please selecte a template.')
            utils.message_dialog(error_msg, gtk.MESSAGE_WARNING)
            return False
        template = Template(filename=template_filename)
        session = bauble.Session()
        values = map(session.merge, objs)
        report = template.render(values=values)
        session.close()
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


formatter_plugin = MakoFormatterPlugin

