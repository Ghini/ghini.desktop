# -*- coding: utf-8 -*-
#
# Copyright 2008-2010 Brett Adams
# Copyright 2012-2016 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
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
import math

import gtk

from mako.template import Template


import bauble.db as db
import bauble.paths as paths
from bauble.plugins.report import FormatterPlugin, SettingsBox
import bauble.utils as utils
import bauble.utils.desktop as desktop


font = {
    '\u200b': 0,
    u'!': 20, u'A': 36, u'a': 31, u'á': 31, u'Á': 38,
    u'"': 23, u'B': 34, u'b': 32, u'à': 31, u'À': 38,
    u'#': 40, u'C': 35, u'c': 28, u'â': 31, u'Â': 38,
    u'$': 32, u'D': 39, u'd': 31, u'å': 31, u'Å': 38,
    u'%': 50, u'E': 32, u'e': 30, u'ä': 31, u'Ä': 38,
    u'&': 46, u'F': 29, u'f': 18, u'ã': 31, u'Ã': 38, u'æ': 31, u'Æ': 38,
    u"'": 13, u'G': 39, u'g': 31, u'ç': 28, u'Ç': 35,
    u'(': 22, u'H': 38, u'h': 32, u'ð': 31, u'Ð': 39,
    u')': 23, u'I': 11, u'i': 11, u'é': 30, u'É': 32,
    u'*': 32, u'J': 22, u'j': 11, u'è': 30, u'È': 31,
    u'+': 41, u'K': 35, u'k': 29, u'ê': 30, u'Ê': 32,
    u',': 18, u'L': 28, u'l': 11, u'ë': 29, u'Ë': 32,
    u'-': 41, u'M': 39, u'm': 52, u'í': 11, u'Í': 11, u'ì': 11, u'Ì': 11,
    u'.': 18, u'N': 37, u'n': 31, u'î': 11, u'Î': 11,
    u'/': 23, u'O': 40, u'o': 31, u'ï': 11, u'Ï': 11,
    u'0': 32, u'P': 31, u'p': 32, u'ñ': 30, u'Ñ': 37,
    u'1': 32, u'Q': 39, u'q': 32, u'ó': 31, u'Ó': 40,
    u'2': 32, u'R': 35, u'r': 22, u'ò': 31, u'Ò': 40,
    u'3': 32, u'S': 34, u's': 27, u'ô': 31, u'Ô': 40,
    u'4': 32, u'T': 29, u't': 18, u'ö': 31, u'Ö': 40,
    u'5': 32, u'U': 37, u'u': 32, u'õ': 31, u'Õ': 40,
    u'6': 32, u'V': 36, u'v': 27, u'ø': 31, u'Ø': 40,
    u'7': 32, u'W': 49, u'w': 41, u'ú': 32, u'Ú': 37,
    u'8': 32, u'X': 34, u'x': 29, u'ù': 31, u'Ù': 36,
    u'9': 32, u'Y': 31, u'y': 27, u'û': 32, u'Û': 37,
    u':': 18, u'Z': 34, u'z': 26, u'ü': 32, u'Ü': 37,
    u';': 18, u'[': 23, u'{': 32, u'ý': 29, u'Ý': 30,
    u'<': 41, u'\\': 23, u'|': 23, u'ÿ': 30, u'Ÿ': 31,
    u'=': 41, u']': 23, u'}': 32, u'ń': 31, u'Ń': 38,
    u'>': 41, u'^': 40, u'~': 41, u'ł': 15, u'Ł': 27,
    u'?': 27, u'_': 32, u' ': 18, u'č': 26, u'Č': 35,
    u'@': 50, u'`': 32, u'×': 26, u'š': 26, u'Š': 35,
    }


def add_text(x, y, s, size, align=0, italic=False, strokes=1, rotate=0):
    """compute the `use` elements to be added and the width of the result

    align 0: left; align 1: right; align 0.5: centre

    the returned value is a 3-tuple, where the first element is the
    string to be added to the svg, second and third element are the next
    insertion point if you want to continue the text on the same line
    with different attributes.
    """
    result_list = []
    totalwidth = 0
    if not s:
        return '', x, y
    for i in s:
        if i not in font:
            i = u'?'
        glyph_wid = font[i] / 2.0
        glyph_ref = "s%d-u%04x" % (strokes, ord(i))
        result_list.append(
            '<use transform="translate(%s,0)" xlink:href="#%s"/>' %
            (totalwidth, glyph_ref))
        totalwidth += glyph_wid
    radians = rotate / 180.0 * math.pi
    if align != 0:
        x -= (totalwidth * size) * align * math.cos(radians)
        y -= (totalwidth * size) * align * math.sin(radians)
    italic_text = italic and 'matrix(1,0,-0.1,1,2,0)' or ''
    rotate_text = rotate and ('rotate(%s)' % rotate) or ''
    # we can't do the following before having placed all glyphs
    result_list.insert(
        0, (('<g transform="translate(%s, %s)scale(%s)' + italic_text + rotate_text + '">')
            % (round(x, 6), round(y, 6), size)))
    result_list.append('</g>')
    result = "\n".join(result_list)
    return (result,
            x + totalwidth * size * math.cos(radians),
            y + totalwidth * size * math.sin(radians))


def add_code39(x, y, s, unit=1, height=10, align=0, colour='#0000ff'):
    result_list = []
    cumulative_x = 0
    if not s:
        return '', x, y
    s = '!' + s + '!'
    for i in s:
        if i not in Code39.MAP.keys():
            i = u' '
        result_list.append(Code39.letter(i, height, translate=(cumulative_x, 0), colour=colour))
        cumulative_x += 16
    cumulative_x -= 1
    shift = -align * cumulative_x
    result_list.insert(
        0, ('<g transform="translate(%s,%s)scale(%s,1)translate(%s,0)">' % (x, y, unit, shift)))
    result_list.append('</g>')
    return ''.join(result_list), x + cumulative_x + shift, y


class Code39:
    # Class for encoding as Code39 barcode.

    # Every symbol gets encoded as a sequence of 5 black bars separated by 4
    # white spaces. Bars and spaces may be thin (one unit), or thick (three
    # units). A thin white space separates the sequences. All barcodes start
    # and end with a single special symbol (we call it '!') which isn't
    # included in the 45 encodable characters.

    MAP = {'!': 'b   b bbb bbb b',
           '7': 'b b   b bbb bbb',
           '-': 'b   b b bbb bbb',
           '4': 'b b   bbb b bbb',
           'X': 'b   b bbb b bbb',
           '0': 'b b   bbb bbb b',
           '.': 'bbb   b b bbb b',
           '1': 'bbb b   b b bbb',
           '3': 'bbb bbb   b b b',
           '2': 'b bbb   b b bbb',
           '5': 'bbb b   bbb b b',
           '6': 'b bbb   bbb b b',
           '9': 'b bbb   b bbb b',
           '8': 'bbb b   b bbb b',
           ' ': 'b   bbb b bbb b',
           '.': 'bbb   b b bbb b',
           'A': 'bbb b b   b bbb',
           'C': 'bbb bbb b   b b',
           'B': 'b bbb b   b bbb',
           'E': 'bbb b bbb   b b',
           'D': 'b b bbb   b bbb',
           'G': 'b b b   bbb bbb',
           'F': 'b bbb bbb   b b',
           'I': 'b bbb b   bbb b',
           'H': 'bbb b b   bbb b',
           'K': 'bbb b b b   bbb',
           'J': 'b b bbb   bbb b',
           'M': 'bbb bbb b b   b',
           'L': 'b bbb b b   bbb',
           'O': 'bbb b bbb b   b',
           'N': 'b b bbb b   bbb',
           'Q': 'b b b bbb   bbb',
           'P': 'b bbb bbb b   b',
           'S': 'b bbb b bbb   b',
           'R': 'bbb b b bbb   b',
           'U': 'bbb   b b b bbb',
           'T': 'b b bbb bbb   b',
           'W': 'bbb   bbb b b b',
           'V': 'b   bbb b b bbb',
           'Y': 'bbb   b bbb b b',
           'Z': 'b   bbb bbb b b',
           '%': 'b b   b   b   b',
           '$': 'b   b   b   b b',
           '+': 'b   b b   b   b',
           '/': 'b   b   b b   b',
    }
    @classmethod
    def path(cls, letter, height):
        format = ('M %(0)s,0 %(0)s,H M %(1)s,H %(1)s,0 '
                  'M %(2)s,0 %(2)s,H M %(3)s,H %(3)s,0 '
                  'M %(4)s,0 %(4)s,H')
        if not letter in '%$+/':
             format += (' M %(5)s,H %(5)s,0 '
                        'M %(6)s,0 %(6)s,H M %(7)s,H %(7)s,0 '
                        'M %(8)s,0 %(8)s,H')
        format = format.replace('H', str(height))
        blacks = [i for i, x in enumerate(cls.MAP[letter]) if x=='b']
        d = dict(zip((str(i) for i in range(10)), blacks))
        return format % d

    @classmethod
    def letter(cls, letter, height, translate=None, colour='#0000ff'):
        if translate is not None:
            transform_text = ' transform="translate(%s,%s)"' % translate
        else:
            transform_text = ''
        return '<path%(transform)s d="%(path)s" style="stroke:%(colour)s;stroke-width:1"/>' % {
            'transform': transform_text,
            'path': cls.path(letter, height),
            'colour': colour,
        }

    
class add_qr_functor:
    import pyqrcode
    def __init__(self):
        import StringIO
        import re
        self.buffer = StringIO.StringIO()
        self.pattern = {
            'svg': re.compile('<svg.*height="([0-9]*)".*>(<path.*>)</svg>'),
            'ps': re.compile('.* ([0-9]*).*(^/M.*)%%EOF.*', re.MULTILINE | re.DOTALL),
        }

    def __call__(self, x, y, text, scale=1, side=None, format='svg'):
        qr = self.pyqrcode.create(text)
        self.buffer.truncate(0)
        self.buffer.seek(0)
        if format == 'svg':
            qr.svg(self.buffer, xmldecl=False, quiet_zone=0, scale=scale)
        else:
            qr.eps(self.buffer, quiet_zone=0)
        match = self.pattern[format].match(self.buffer.getvalue())
        result_list = [match.group(2)]
        transform = []
        if x != 0 or y != 0:
            if format == 'ps':
                transform.append("%s %s translate" % (x, y))
            else:
                transform.append("translate(%s,%s)" % (x, y))
        if side is not None:
            orig_side = float(match.group(1))
            if format == 'ps':
                transform.append("%s %s scale" % (side / orig_side, side / orig_side))
            else:
                transform.append("scale(%s)" % (side / orig_side))
        if transform:
            if format == 'ps':
                result_list = transform + result_list
            else:
                result_list.insert(0, '<g transform="%s">' % (''.join(transform)))
                result_list.append('</g>')
        if format == 'ps':
            result_list = ['gsave'] + result_list + ["grestore"]
        return '\n'.join(result_list)

add_qr = add_qr_functor()
    

class MakoFormatterSettingsBox(SettingsBox):
    import re
    pattern = re.compile("^## OPTION ([a-z_]*): \("
                         "type: ([a-z_]*), "
                         "default: '(.*)', "
                         "tooltip: '(.*)'\)$")

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
        self.widgets.template_chooser.connect('file-set', self.on_file_set)
        self.defaults = []

    def get_settings(self):
        """
        """
        return {'template': self.widgets.template_chooser.get_filename(),
                'private': self.widgets.private_check.get_active()}

    def update(self, settings):
        if settings.get('template'):
            self.widgets.template_chooser.set_filename(settings['template'])
            self.on_file_set()
        if 'private' in settings:
            self.widgets.private_check.set_active(settings['private'])

    def on_file_set(self, *args, **kwargs):
        self.defaults = []
        options_box = self.widgets.mako_options_box
        # empty the options box
        map(options_box.remove, options_box.get_children())
        # which options does the template accept? (can be None)
        try:
            with open(self.widgets.template_chooser.get_filename()) as f:
                # scan the header filtering lines starting with # OPTION
                option_lines = filter(None,
                                      [self.pattern.match(i.strip())
                                       for i in f.readlines()])
        except IOError:
            option_lines = []

        option_fields = [i.groups() for i in option_lines]
        from bauble.plugins.report import options
        current_row = 0
        # populate the options box
        for fname, ftype, fdefault, ftooltip in option_fields:
            row = gtk.HBox()
            label = gtk.Label(fname.replace('_', ' ') + _(':'))
            label.set_alignment(0, 0.5)
            entry = gtk.Entry()
            options.setdefault(fname, fdefault)
            entry.set_text(options[fname])
            entry.set_tooltip_text(ftooltip)
            # entry updates the corresponding item in report.options
            entry.connect('changed', self.set_option, fname)
            self.defaults.append((entry, fdefault))
            options_box.attach(label, 0, 1, current_row, current_row+1,
                               xoptions=gtk.FILL)
            options_box.attach(entry, 1, 2, current_row, current_row+1,
                               xoptions=gtk.FILL)
            current_row += 1
        if self.defaults:
            button = gtk.Button(_('Reset to defaults'))
            button.connect('clicked', self.reset_options)
            options_box.attach(button, 0, 2, current_row, current_row+1,
                               xoptions=gtk.FILL)
        options_box.show_all()

    def reset_options(self, widget):
        for entry, text in self.defaults:
            entry.set_text(text)

    def set_option(self, widget, fname):
        from bauble.plugins.report import options
        options[fname] = widget.get_text()


_settings_box = MakoFormatterSettingsBox()


class MakoFormatterPlugin(FormatterPlugin):
    """
    The MakoFormatterPlugins passes the values in the search
    results directly to a Mako template.  It is up to the template
    author to validate the type of the values and act accordingly if not.
    """

    title = 'Mako'

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

        src_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'mako', 'templates')
        for template in os.listdir(src_dir):
            if template.endswith('~'):
                continue
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

        # make sure the options dictionary is initialized at all
        with open(template_filename) as f:
            option_lines = filter(None,
                                  [MakoFormatterSettingsBox.pattern.match(i.strip())
                                   for i in f.readlines()])
        option_fields = [i.groups() for i in option_lines]
        from bauble.plugins.report import options
        for fname, ftype, fdefault, ftooltip in option_fields:
            options.setdefault(fname, fdefault)

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
