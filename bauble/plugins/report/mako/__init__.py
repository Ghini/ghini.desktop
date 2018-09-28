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
import re

from gi.repository import Gtk

from mako.template import Template


import bauble.db as db
import bauble.paths as paths
from bauble.plugins.report import FormatterPlugin
import bauble.utils as utils
import bauble.utils.desktop as desktop


font = {
    '\\u200b': 0,
    '!': 20, 'A': 36, 'a': 31, 'á': 31, 'Á': 38,
    '"': 23, 'B': 34, 'b': 32, 'à': 31, 'À': 38,
    '#': 40, 'C': 35, 'c': 28, 'â': 31, 'Â': 38,
    '$': 32, 'D': 39, 'd': 31, 'å': 31, 'Å': 38,
    '%': 50, 'E': 32, 'e': 30, 'ä': 31, 'Ä': 38,
    '&': 46, 'F': 29, 'f': 18, 'ã': 31, 'Ã': 38, 'æ': 31, 'Æ': 38,
    "'": 13, 'G': 39, 'g': 31, 'ç': 28, 'Ç': 35,
    '(': 22, 'H': 38, 'h': 32, 'ð': 31, 'Ð': 39,
    ')': 23, 'I': 11, 'i': 11, 'é': 30, 'É': 32,
    '*': 32, 'J': 22, 'j': 11, 'è': 30, 'È': 31,
    '+': 41, 'K': 35, 'k': 29, 'ê': 30, 'Ê': 32,
    ',': 18, 'L': 28, 'l': 11, 'ë': 29, 'Ë': 32,
    '-': 41, 'M': 39, 'm': 52, 'í': 11, 'Í': 11, 'ì': 11, 'Ì': 11,
    '.': 18, 'N': 37, 'n': 31, 'î': 11, 'Î': 11,
    '/': 23, 'O': 40, 'o': 31, 'ï': 11, 'Ï': 11,
    '0': 32, 'P': 31, 'p': 32, 'ñ': 30, 'Ñ': 37,
    '1': 32, 'Q': 39, 'q': 32, 'ó': 31, 'Ó': 40,
    '2': 32, 'R': 35, 'r': 22, 'ò': 31, 'Ò': 40,
    '3': 32, 'S': 34, 's': 27, 'ô': 31, 'Ô': 40,
    '4': 32, 'T': 29, 't': 18, 'ö': 31, 'Ö': 40,
    '5': 32, 'U': 37, 'u': 32, 'õ': 31, 'Õ': 40,
    '6': 32, 'V': 36, 'v': 27, 'ø': 31, 'Ø': 40,
    '7': 32, 'W': 49, 'w': 41, 'ú': 32, 'Ú': 37,
    '8': 32, 'X': 34, 'x': 29, 'ù': 31, 'Ù': 36,
    '9': 32, 'Y': 31, 'y': 27, 'û': 32, 'Û': 37,
    ':': 18, 'Z': 34, 'z': 26, 'ü': 32, 'Ü': 37,
    ';': 18, '[': 23, '{': 32, 'ý': 29, 'Ý': 30,
    '<': 41, '\\': 23, '|': 23, 'ÿ': 30, 'Ÿ': 31,
    '=': 41, ']': 23, '}': 32, 'ń': 31, 'Ń': 38,
    '>': 41, '^': 40, '~': 41, 'ł': 15, 'Ł': 27,
    '?': 27, '_': 32, ' ': 18, 'č': 26, 'Č': 35,
    '@': 50, '`': 32, '×': 26, 'š': 26, 'Š': 35,
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
            i = '?'
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
    '''return svg code corresponding to barcode for string s
    '''
    result_list = []
    cumulative_x = 0
    if not s:
        return '', x, y
    s = '!' + s + '!'
    for i in s:
        if i not in list(Code39.MAP.keys()):
            i = ' '
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
        d = dict(list(zip((str(i) for i in range(10)), blacks)))
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
    '''add a QR code, to either svg & ps output.

    functor: function with persistent data
    '''
    import pyqrcode
    def __init__(self):
        self.pattern = {
            'svg': re.compile('<svg.*height="([0-9]*)".*>(<path.*>)</svg>'),
            'ps': re.compile('.* ([0-9]*).*(^/M.*)%%EOF.*', re.MULTILINE | re.DOTALL),
        }

    def __call__(self, x, y, text, scale=1, side=None, format='svg'):
        import io
        qr = self.pyqrcode.create(text)
        if format == 'svg':
            self.buffer = io.BytesIO()
            qr.svg(self.buffer, xmldecl=False, quiet_zone=0, scale=scale)
            match = self.pattern[format].match(self.buffer.getvalue().decode())
        else:
            self.buffer = io.StringIO()
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
        result = '\n'.join(result_list)
        logging.debug("qr-svg: %s(%s)" % (type(result).__name__, result))
        return result

add_qr = add_qr_functor()
    

def insert_picture(left, bottom, width, height, image):
    '''postscript string that corresponds to placing image in page

    left, bottom specify position of bottom-left corner of picture.

    width, height give dimension of picture on paper.  either width or
    height may be None (not both), in which case proportions are kept.

    image is a PIL.Image object, it needs be RBG (not indexed) and
    transparency is ignored.

    '''

    import itertools
    width0, height0 = image.size
    if width is None:
        width = height * (1.0 * width0 / height0)
    if height is None:
        height = width * (1.0 * height0 / width0)
    result = ('gsave %(left)d %(bottom)d translate %(width)d %(height)d scale %(width0)d %(height0)d 8 [%(width0)d 0 0 -%(height0)d 0 %(height0)d] (%(text)s>) /ASCIIHexDecode filter false 3 colorimage grestore\n' % {
        'left': left,
        'bottom': bottom,
        'width0': width0,
        'height0': height0,
        'width': width,
        'height': height,
        'text': ''.join([("%02x" % g) for g in itertools.chain.from_iterable(k[:3] for k in image.getdata())])})
    return result


def insert_jpeg_picture(left, bottom, width, height, filename):
    '''postscript string that corresponds to placing JPEG image in page

    left, bottom specify position of bottom-left corner of picture.

    width, height give dimension of picture on paper.  either width or
    height may be None (not both), in which case proportions are kept.

    filename is a full path to a JPEG image.

    '''
    import PIL.Image
    tmp = PIL.Image.open(filename)
    width0, height0 = tmp.size
    if width is None:
        width = height * (1.0 * width0 / height0)
    if height is None:
        height = width * (1.0 * height0 / width0)
    
    content = open(filename, "rb").read()
    return('gsave %(left)d %(bottom)d translate %(width)d %(height)d scale %(width0)d %(height0)d 8 [%(width0)d 0 0 -%(height0)d 0 %(height0)d] (%(text)s>) /ASCIIHexDecode filter 0 dict /DCTDecode filter false 3 colorimage grestore\n' % {
        'left': left,
        'bottom': bottom,
        'width0': width0,
        'height0': height0,
        'width': width,
        'height': height,
        'text': ''.join(["%02x" % g for g in content])})


class MakoFormatterPlugin(FormatterPlugin):
    """
    The MakoFormatterPlugins passes the values in the search
    results directly to a Mako template.  It is up to the template
    author to validate the type of the values and act accordingly if not.
    """

    title = 'Mako'
    domain_pattern = re.compile(r"^##\s*DOMAIN\s+([a-z_]*)\s*$")
    option_pattern = re.compile("^## OPTION ([a-z_]*): \("
                                "type: ([a-z_]*), "
                                "default: '(.*)', "
                                "tooltip: '(.*)'\)$")

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
        cls.templates = []
        src_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'mako', 'templates')
        for template in list(os.walk(src_dir))[0][2]:
            if template.endswith('~'):
                continue
            if template.startswith('__'):
                continue
            cls.templates.append(template)
        
    @classmethod
    def init(cls):
        """copy default template files to appdata_dir

        we do this in the initialization instead of installation
        because new version of plugin might provide new templates.

        """
        super().init()

        src_dir = os.path.join(paths.lib_dir(), "plugins", "report", 'mako', 'templates')
        for template in cls.templates:
            src = os.path.join(src_dir, template)
            dst = os.path.join(cls.plugin_dir, template)
            if not os.path.exists(dst) and os.path.exists(src):
                shutil.copy(src, dst)

    @staticmethod
    def format(objs, **kwargs):
        template_filename = kwargs['template']
        use_private = kwargs.get('private', True)
        if not template_filename:
            msg = _('Please select a template.')
            utils.idle_message(msg, Gtk.MessageType.WARNING)
            return False
        try:
            template = Template(filename=template_filename,
                                input_encoding='utf-8', output_encoding='utf-8')
        except RuntimeError as e:
            import traceback
            utils.idle_message("Reading template %s\n%s(%s)\n%s" % (template_filename, type(e).__name__, e, traceback.format_exc()), type=Gtk.MessageType.ERROR)
            return False

        session = db.Session()
        values = list(map(session.merge, objs))
        report = template.render(values=values, options=kwargs)
        session.close()
        # assume the template is the same file type as the output file
        head, ext = os.path.splitext(template_filename)
        fd, filename = tempfile.mkstemp(suffix=ext)
        os.write(fd, report)
        os.close(fd)
        try:
            desktop.open("file://%s" % filename)
        except OSError:
            utils.message_dialog(_('Could not open the report with the '
                                   'default program. You can open the '
                                   'file manually at %s') % filename)
        return report


formatter_plugin = MakoFormatterPlugin
