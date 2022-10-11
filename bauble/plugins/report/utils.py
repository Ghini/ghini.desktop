# -*- coding: utf-8 -*-
#
# Copyright 2015-2018 Mario Frasca <mario@anche.no>.
# Copyright 2017 Jardín Botánico de Quito
# Copyright 2018 Tanager Botanical Garden
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

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

import re
import math
import os.path


class SVG:
    '''not a class, more a namespace - cfr PS'''
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

    @classmethod
    def add_text(cls, x, y, s, size, align=0, italic=False, strokes=1, rotate=0):
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
            if i not in cls.font:
                i = '?'
            glyph_wid = cls.font[i] / 2.0
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

    @classmethod
    def add_code39(cls, x, y, s, unit=1, height=10, align=0, colour='#0000ff'):
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

    @classmethod
    def add_qr(cls, x, y, text, scale=1, side=None):
        return add_qr(x, y, text, scale, side, format='svg')


class PS:
    '''not a class, more a namespace - cfr SVG'''

    font = {
        'serif':
        {
            ' ': ('5F', 12), '\u200b': ('5F',  0),
            '!': ('01', 17), 'A': ('21', 32), 'a': ('41', 24),
            '"': ('02', 20), 'B': ('22', 33), 'b': ('42', 25),
            '#': ('03', 25), 'C': ('23', 34), 'c': ('43', 22),
            '$': ('04', 25), 'D': ('24', 36), 'd': ('44', 25),
            '%': ('05', 43), 'E': ('25', 31), 'e': ('45', 23),
            '&': ('06', 38), 'F': ('26', 28), 'f': ('46', 16),
            "'": ('07',  9), 'G': ('27', 36), 'g': ('47', 26),
            '(': ('08', 17), 'H': ('28', 36), 'h': ('48', 25),
            ')': ('09', 16), 'I': ('29', 17), 'i': ('49', 12),
            '*': ('0A', 25), 'J': ('2A', 20), 'j': ('4A', 12),
            '+': ('0B', 28), 'K': ('2B', 35), 'k': ('4B', 27),
            ',': ('0C', 13), 'L': ('2C', 31), 'l': ('4C', 13),
            '-': ('0D', 17), 'M': ('2D', 44), 'm': ('4D', 38),
            '.': ('0E', 12), 'N': ('2E', 36), 'n': ('4E', 25),
            '/': ('0F', 14), 'O': ('2F', 36), 'o': ('4F', 26),
            '0': ('10', 28), 'P': ('30', 28), 'p': ('50', 25),
            '1': ('11', 28), 'Q': ('31', 36), 'q': ('51', 24),
            '2': ('12', 28), 'R': ('32', 34), 'r': ('52', 18),
            '3': ('13', 28), 'S': ('33', 27), 's': ('53', 19),
            '4': ('14', 28), 'T': ('34', 31), 't': ('54', 15),
            '5': ('15', 28), 'U': ('35', 36), 'u': ('55', 26),
            '6': ('16', 28), 'V': ('36', 37), 'v': ('56', 24),
            '7': ('17', 28), 'W': ('37', 46), 'w': ('57', 36),
            '8': ('18', 28), 'X': ('38', 36), 'x': ('58', 26),
            '9': ('19', 28), 'Y': ('39', 37), 'y': ('59', 24),
            ':': ('1A', 15), 'Z': ('3A', 30), 'z': ('5A', 22),
            ';': ('1B', 13), '[': ('3B', 17), '{': ('5B', 24),
            '<': ('1C', 28), '\\':('3C', 14), '|': ('5C', 20),
            '=': ('1D', 28), ']': ('3D', 17), '}': ('5D', 24),
            '>': ('1E', 29), '^': ('3E', 23), '~': ('5E', 27),
            '?': ('1F', 21), '_': ('3F', 25),
            '@': ('20', 47), '`': ('40', 17),
            'À': ('82', 36),
            'Á': ('81', 37),
            'Â': ('83', 36),
            'Ã': ('86', 36),
            'Ä': ('85', 36),
            'Å': ('84', 36),
            'Ç': ('87', 33),
            'Č': ('9F', 33),
            'È': ('8A', 31),
            'É': ('89', 31),
            'Ê': ('8B', 30),
            'Ë': ('8C', 31),
            'Í': ('8D', 16),
            'Î': ('8E', 17),
            'Ï': ('8F', 17),
            'Ð': ('88', 36),
            'Ł': ('9E', 31),
            'Ñ': ('90', 36),
            'Ń': ('9D', 36),
            'Ò': ('92', 36),
            'Ó': ('91', 36),
            'Ô': ('93', 36),
            'Õ': ('95', 36),
            'Ö': ('94', 36),
            'Ø': ('96', 37),
            'Š': ('A0', 28),
            'Ù': ('98', 36),
            'Ú': ('97', 36),
            'Û': ('99', 36),
            'Ü': ('9A', 36),
            'Ý': ('9B', 36),
            'Ÿ': ('9C', 36),
            'à': ('62', 22),
            'á': ('61', 23),
            'â': ('63', 22),
            'ã': ('66', 23),
            'ä': ('65', 22),
            'å': ('64', 22),
            'ç': ('67', 22),
            'č': ('7F', 23),
            'è': ('6A', 22),
            'é': ('69', 22),
            'ê': ('6B', 22),
            'ë': ('6C', 23),
            'í': ('6D', 12),
            'î': ('6E', 12),
            'ï': ('6F', 12),
            'ł': ('7E', 12),
            'ñ': ('70', 24),
            'ń': ('7D', 26),
            'ð': ('68', 25),
            'ò': ('72', 26),
            'ó': ('71', 25),
            'ô': ('73', 25),
            'õ': ('75', 26),
            'ö': ('74', 25),
            'ø': ('76', 25),
            'š': ('80', 19),
            'ù': ('78', 25),
            'ú': ('77', 24),
            'û': ('79', 25),
            'ü': ('7A', 26),
            'ý': ('7B', 25),
            'ÿ': ('7C', 24),
            '×': ('60', 23),
        },
        'sans': {
            ' ': ('5F', 18), '\u200b': ('5F',  0),
            '!': ('01', 20), 'A': ('21', 34), 'a': ('41', 30),
            '"': ('02', 23), 'B': ('22', 34), 'b': ('42', 31),
            '#': ('03', 40), 'C': ('23', 35), 'c': ('43', 26),
            '$': ('04', 32), 'D': ('24', 39), 'd': ('44', 31),
            '%': ('05', 54), 'E': ('25', 32), 'e': ('45', 30),
            '&': ('06', 37), 'F': ('26', 28), 'f': ('46', 18),
            "'": ('07', 13), 'G': ('27', 39), 'g': ('47', 31),
            '(': ('08', 22), 'H': ('28', 38), 'h': ('48', 31),
            ')': ('09', 23), 'I': ('29', 21), 'i': ('49', 12),
            '*': ('0A', 32), 'J': ('2A', 22), 'j': ('4A', 15),
            '+': ('0B', 41), 'K': ('2B', 35), 'k': ('4B', 29),
            ',': ('0C', 18), 'L': ('2C', 28), 'l': ('4C', 12),
            '-': ('0D', 23), 'M': ('2D', 42), 'm': ('4D', 48),
            '.': ('0E', 18), 'N': ('2E', 37), 'n': ('4E', 32),
            '/': ('0F', 23), 'O': ('2F', 40), 'o': ('4F', 31),
            '0': ('10', 32), 'P': ('30', 30), 'p': ('50', 30),
            '1': ('11', 32), 'Q': ('31', 39), 'q': ('51', 32),
            '2': ('12', 32), 'R': ('32', 35), 'r': ('52', 21),
            '3': ('13', 32), 'S': ('33', 34), 's': ('53', 26),
            '4': ('14', 32), 'T': ('34', 31), 't': ('54', 20),
            '5': ('15', 32), 'U': ('35', 37), 'u': ('55', 31),
            '6': ('16', 32), 'V': ('36', 34), 'v': ('56', 30),
            '7': ('17', 32), 'W': ('37', 49), 'w': ('57', 41),
            '8': ('18', 32), 'X': ('38', 34), 'x': ('58', 29),
            '9': ('19', 32), 'Y': ('39', 31), 'y': ('59', 30),
            ':': ('1A', 23), 'Z': ('3A', 34), 'z': ('5A', 26),
            ';': ('1B', 23), '[': ('3B', 23), '{': ('5B', 32),
            '<': ('1C', 41), '\\':('3C', 23), '|': ('5C', 23),
            '=': ('1D', 41), ']': ('3D', 23), '}': ('5D', 32),
            '>': ('1E', 41), '^': ('3E', 40), '~': ('5E', 41),
            '?': ('1F', 27), '_': ('3F', 32),
            '@': ('20', 50), '`': ('40', 32), 
            'À': ('82', 34),
            'Á': ('81', 35),
            'Â': ('83', 34),
            'Ã': ('86', 34),
            'Ä': ('85', 34),
            'Å': ('84', 34),
            'Ç': ('87', 35),
            'È': ('8A', 31),
            'É': ('89', 32),
            'Ê': ('8B', 32),
            'Ë': ('8C', 32),
            'Í': ('8D', 21),
            'Î': ('8E', 21),
            'Ï': ('8F', 21),
            'Ð': ('88', 39),
            'Ł': ('9E', 27),
            'Ñ': ('90', 37),
            'Ò': ('92', 40),
            'Ó': ('91', 39),
            'Ô': ('93', 39),
            'Õ': ('95', 39),
            'Ö': ('94', 40),
            '×': ('60', 26),
            'Ø': ('96', 39),
            'Ù': ('98', 36),
            'Ú': ('97', 37),
            'Û': ('99', 37),
            'Ü': ('9A', 37),
            'Ý': ('9B', 30),
            'à': ('62', 30),
            'á': ('61', 30),
            'â': ('63', 30),
            'ã': ('66', 30),
            'ä': ('65', 30),
            'å': ('64', 30),
            'ç': ('67', 26),
            'è': ('6A', 30),
            'é': ('69', 30),
            'ê': ('6B', 30),
            'ë': ('6C', 29),
            'í': ('6D', 12),
            'î': ('6E', 12),
            'ï': ('6F', 12),
            'ł': ('7E', 15),
            'ð': ('68', 31),
            'ñ': ('70', 32),
            'ò': ('72', 30),
            'ó': ('71', 30),
            'ô': ('73', 30),
            'õ': ('75', 30),
            'ö': ('74', 31),
            'ø': ('76', 30),
            'ù': ('78', 31),
            'ú': ('77', 32),
            'û': ('79', 32),
            'ü': ('7A', 32),
            'ý': ('7B', 29),
            'ÿ': ('7C', 30),
            'Č': ('9F', 35),
            'č': ('7F', 26),
            'Ń': ('9D', 38),
            'ń': ('7D', 31),
            'Š': ('A0', 35),
            'š': ('80', 26),
            'Ÿ': ('9C', 31),
        },
    }

    @classmethod
    def add_text(cls, x, y, s, style='sans', size=12, align=0, stretch=1, maxwidth=None):
        import sys
        s = (s or '').replace('\u200b', '')
        glyphs = ['<']
        widths = ['[']
        totalwidth = 0
        qmark = cls.font[style]['?']
        for i in s or []:
            glyph_def = cls.font[style].get(i, qmark)
            glyphs.append(glyph_def[0])
            w = round((0.28 * glyph_def[1]) * size + 0.5, 1)
            totalwidth += w
            widths.append("%0.1f" % w)
        glyphs.append('>')
        widths.append(']')
        if maxwidth is not None and totalwidth > maxwidth:
            hfactor = 1.0 * maxwidth / totalwidth
            totalwidth = maxwidth
        else:
            hfactor = 1
        x -= totalwidth * align
        result = ["%0.1f %0.1f moveto" % (x, y, ),
                  ''.join(glyphs),
                  ' '.join(widths),
                  "xshow"]
        if hfactor != 1 or stretch != 1:
            result.insert(1, "gsave")
            result.insert(2, "%0.3f %0.1f scale" % (hfactor, stretch, ))
            result.append("grestore")

        return '\n'.join(result)

    @classmethod
    def add_qr(cls, x, y, text, scale=1, side=None):
        return add_qr(x, y, text, scale, side, format='ps')

    @classmethod
    def insert_picture(cls, left, bottom, width, height, name):
        '''postscript string that corresponds to placing image in page

        left, bottom specify position of bottom-left corner of picture.

        width, height give dimension of picture on paper.  either width or
        height may be None (not both), in which case proportions are kept.

        image is a filename, which we open here.

        PIL.Image object, it needs be RBG or grey-scale (not indexed) and
        transparency, if present, is converted to levels of white.

        '''
        import PIL.Image
        image = PIL.Image.open(os.path.join(get_caller_template_location(), name))
        import itertools
        width0, height0 = image.size
        if width is None:
            width = height * (1.0 * width0 / height0)
        if height is None:
            height = width * (1.0 * height0 / width0)
        channels = len(image.mode.strip('A'))
        try:
            chain = list(itertools.chain.from_iterable(k[:channels] for k in image.getdata()))
        except:
            chain = image.getdata()
        result = ('gsave %(left)d %(bottom)d translate %(width)d %(height)d scale %(width0)d %(height0)d 8 [%(width0)d 0 0 -%(height0)d 0 %(height0)d] (%(text)s>) /ASCIIHexDecode filter false %(channels)s colorimage grestore\n' % {
            'left': left,
            'bottom': bottom,
            'width0': width0,
            'height0': height0,
            'width': width,
            'height': height,
            'channels': channels,
            'text': ''.join([("%02x" % g) for g in chain])})
        return result

    @classmethod
    def insert_jpeg_picture(cls, left, bottom, width, height, name):
        '''postscript string that corresponds to placing JPEG image in page

        left, bottom specify position of bottom-left corner of picture.

        width, height give dimension of picture on paper.  either width or
        height may be None (not both), in which case proportions are kept.

        filename is a full path to a JPEG image.

        '''
        import PIL.Image
        filename = os.path.join(get_caller_template_location(), name)
        image = PIL.Image.open(filename)
        width0, height0 = image.size
        channels = len(image.mode.strip('A'))
        if width is None:
            width = height * (1.0 * width0 / height0)
        if height is None:
            height = width * (1.0 * height0 / width0)

        content = open(filename, "rb").read()
        return('gsave %(left)d %(bottom)d translate %(width)d %(height)d scale %(width0)d %(height0)d 8 [%(width0)d 0 0 -%(height0)d 0 %(height0)d] (%(text)s>) /ASCIIHexDecode filter 0 dict /DCTDecode filter false %(channels)s colorimage grestore\n' % {
            'left': left,
            'bottom': bottom,
            'width0': width0,
            'height0': height0,
            'width': width,
            'height': height,
            'channels': channels,
            'text': ''.join(["%02x" % g for g in content])})


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
        logger.debug("qr-svg: %s(%s)" % (type(result).__name__, result))
        return result

add_qr = add_qr_functor()
    

def get_caller_template_location():
    '''return location of caller template

    invoked from a function during template rendering, returns the location
    of the template being rendered.

    '''
    try:
        import sys
        import os.path
        here = sys._getframe()
        # Mako names it 'render_body', Jinja2 'block_body'
        while here.f_code.co_name not in ['render_body', 'block_body']:
            here = here.f_back
        template_name = here.f_code.co_filename
        if here.f_code.co_name == 'render_body':
            from mako import template  # Mako hides the full path
            info = mako.template._get_module_info(template_name)
            template_name = info.template_filename
        return os.path.dirname(template_name)
    except Exception as e:
        logger.debug("%s(%s)" % (type(e).__name__, e))
        return ''
