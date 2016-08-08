# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2016 Mario Frasca <mario@anche.no>.
#
# This file is part of ghini.desktop.
#
# ghini.desktop is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ghini.desktop is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
#
# report/mako/
#

import logging
logger = logging.getLogger(__name__)

import os
import shutil
import tempfile

import gtk

from mako.template import Template

from bauble.i18n import _
import bauble.db as db
import bauble.paths as paths
from bauble.plugins.report import FormatterPlugin, SettingsBox
import bauble.utils as utils
import bauble.utils.desktop as desktop


class MakoFormatterSettingsBox(SettingsBox):

    def __init__(self, report_dialog=None, *args):
        super(MakoFormatterSettingsBox, self).__init__(*args)
        self.widgets = utils.load_widgets(
            os.path.join(paths.lib_dir(),
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

    @classmethod
    def install(cls, import_defaults=True):
        "create templates dir on plugin installation"
        logger.debug("installing mako plugin")
        container_dir = os.path.join(paths.appdata_dir(), "templates")
        if not os.path.exists(container_dir):
            os.mkdir(container_dir)
        cls.plugin_dir = os.path.join(paths.appdata_dir(), "templates", "mako")
        if not os.path.exists(cls.plugin_dir):
            os.mkdir(cls.plugin_dir)

    @classmethod
    def init(cls):
        """copy default template files to appdata_dir

        we do this in the initialization instead of installation
        because new version of plugin might provide new templates.

        """
        cls.install()  # plugins still not versioned...

        templates = ['example_accession.csv',
                     'example_accession-es.csv',
                     'example_plant.csv',
                     'example_plant-es.csv',
                     'example_species.csv',
                     'example_species-es.csv',
                     'bgci-upload.csv',
                     'label.ps',
                     'labels.html',
                     'labels_small.html',
                     'label-engraving.svg',
        ]
        src_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'mako')
        for template in templates:
            src = os.path.join(src_dir, template)
            dst = os.path.join(cls.plugin_dir, template)
            if not os.path.exists(dst) and os.path.exists(src):
                shutil.copy(src, dst)

    @staticmethod
    def get_settings_box():
        return _settings_box

    @staticmethod
    def format(objs, **kwargs):
        template_filename = kwargs['template']
        use_private = kwargs.get('private', True)
        if not template_filename:
            msg = _('Please select a template.')
            utils.message_dialog(msg, gtk.MESSAGE_WARNING)
            return False
        template = Template(
            filename=template_filename, input_encoding='utf-8',
            output_encoding='utf-8')
        session = db.Session()
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
            utils.message_dialog(_('Could not open the report with the '
                                   'default program. You can open the '
                                   'file manually at %s') % filename)
        return report


formatter_plugin = MakoFormatterPlugin
