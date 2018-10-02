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
            ' ': (u'5F', 12), u'\u200b': (u'5F',  0),
            '!': (u'01', 17), 'A': (u'21', 32), 'a': (u'41', 24),
            '"': (u'02', 20), 'B': (u'22', 33), 'b': (u'42', 25),
            '#': (u'03', 25), 'C': (u'23', 34), 'c': (u'43', 22),
            '$': (u'04', 25), 'D': (u'24', 36), 'd': (u'44', 25),
            '%': (u'05', 43), 'E': (u'25', 31), 'e': (u'45', 23),
            '&': (u'06', 38), 'F': (u'26', 28), 'f': (u'46', 16),
            "'": (u'07',  9), 'G': (u'27', 36), 'g': (u'47', 26),
            '(': (u'08', 17), 'H': (u'28', 36), 'h': (u'48', 25),
            ')': (u'09', 16), 'I': (u'29', 17), 'i': (u'49', 12),
            '*': (u'0A', 25), 'J': (u'2A', 20), 'j': (u'4A', 12),
            '+': (u'0B', 28), 'K': (u'2B', 35), 'k': (u'4B', 27),
            ',': (u'0C', 13), 'L': (u'2C', 31), 'l': (u'4C', 13),
            '-': (u'0D', 17), 'M': (u'2D', 44), 'm': (u'4D', 38),
            '.': (u'0E', 12), 'N': (u'2E', 36), 'n': (u'4E', 25),
            '/': (u'0F', 14), 'O': (u'2F', 36), 'o': (u'4F', 26),
            '0': (u'10', 28), 'P': (u'30', 28), 'p': (u'50', 25),
            '1': (u'11', 28), 'Q': (u'31', 36), 'q': (u'51', 24),
            '2': (u'12', 28), 'R': (u'32', 34), 'r': (u'52', 18),
            '3': (u'13', 28), 'S': (u'33', 27), 's': (u'53', 19),
            '4': (u'14', 28), 'T': (u'34', 31), 't': (u'54', 15),
            '5': (u'15', 28), 'U': (u'35', 36), 'u': (u'55', 26),
            '6': (u'16', 28), 'V': (u'36', 37), 'v': (u'56', 24),
            '7': (u'17', 28), 'W': (u'37', 46), 'w': (u'57', 36),
            '8': (u'18', 28), 'X': (u'38', 36), 'x': (u'58', 26),
            '9': (u'19', 28), 'Y': (u'39', 37), 'y': (u'59', 24),
            ':': (u'1A', 15), 'Z': (u'3A', 30), 'z': (u'5A', 22),
            ';': (u'1B', 13), '[': (u'3B', 17), '{': (u'5B', 24),
            '<': (u'1C', 28), '\\':(u'3C', 14), '|': (u'5C', 20),
            '=': (u'1D', 28), ']': (u'3D', 17), '}': (u'5D', 24),
            '>': (u'1E', 29), '^': (u'3E', 23), '~': (u'5E', 27),
            '?': (u'1F', 21), '_': (u'3F', 25),
            '@': (u'20', 47), '`': (u'40', 17),
            'À': (u'82', 36),
            'Á': (u'81', 37),
            'Â': (u'83', 36),
            'Ã': (u'86', 36),
            'Ä': (u'85', 36),
            'Å': (u'84', 36),
            'Ç': (u'87', 33),
            'Č': (u'9F', 33),
            'È': (u'8A', 31),
            'É': (u'89', 31),
            'Ê': (u'8B', 30),
            'Ë': (u'8C', 31),
            'Í': (u'8D', 16),
            'Î': (u'8E', 17),
            'Ï': (u'8F', 17),
            'Ð': (u'88', 36),
            'Ł': (u'9E', 31),
            'Ñ': (u'90', 36),
            'Ń': (u'9D', 36),
            'Ò': (u'92', 36),
            'Ó': (u'91', 36),
            'Ô': (u'93', 36),
            'Õ': (u'95', 36),
            'Ö': (u'94', 36),
            'Ø': (u'96', 37),
            'Š': (u'A0', 28),
            'Ù': (u'98', 36),
            'Ú': (u'97', 36),
            'Û': (u'99', 36),
            'Ü': (u'9A', 36),
            'Ý': (u'9B', 36),
            'Ÿ': (u'9C', 36),
            'à': (u'62', 22),
            'á': (u'61', 23),
            'â': (u'63', 22),
            'ã': (u'66', 23),
            'ä': (u'65', 22),
            'å': (u'64', 22),
            'ç': (u'67', 22),
            'č': (u'7F', 23),
            'è': (u'6A', 22),
            'é': (u'69', 22),
            'ê': (u'6B', 22),
            'ë': (u'6C', 23),
            'í': (u'6D', 12),
            'î': (u'6E', 12),
            'ï': (u'6F', 12),
            'ł': (u'7E', 12),
            'ñ': (u'70', 24),
            'ń': (u'7D', 26),
            'ð': (u'68', 25),
            'ò': (u'72', 26),
            'ó': (u'71', 25),
            'ô': (u'73', 25),
            'õ': (u'75', 26),
            'ö': (u'74', 25),
            'ø': (u'76', 25),
            'š': (u'80', 19),
            'ù': (u'78', 25),
            'ú': (u'77', 24),
            'û': (u'79', 25),
            'ü': (u'7A', 26),
            'ý': (u'7B', 25),
            'ÿ': (u'7C', 24),
            '×': (u'60', 23),
        },
        'sans': {
            ' ': (u'5F', 18), u'\u200b': (u'5F',  0),
            '!': (u'01', 20), 'A': (u'21', 34), 'a': (u'41', 30),
            '"': (u'02', 23), 'B': (u'22', 34), 'b': (u'42', 31),
            '#': (u'03', 40), 'C': (u'23', 35), 'c': (u'43', 26),
            '$': (u'04', 32), 'D': (u'24', 39), 'd': (u'44', 31),
            '%': (u'05', 54), 'E': (u'25', 32), 'e': (u'45', 30),
            '&': (u'06', 37), 'F': (u'26', 28), 'f': (u'46', 18),
            "'": (u'07', 13), 'G': (u'27', 39), 'g': (u'47', 31),
            '(': (u'08', 22), 'H': (u'28', 38), 'h': (u'48', 31),
            ')': (u'09', 23), 'I': (u'29', 21), 'i': (u'49', 12),
            '*': (u'0A', 32), 'J': (u'2A', 22), 'j': (u'4A', 15),
            '+': (u'0B', 41), 'K': (u'2B', 35), 'k': (u'4B', 29),
            ',': (u'0C', 18), 'L': (u'2C', 28), 'l': (u'4C', 12),
            '-': (u'0D', 23), 'M': (u'2D', 42), 'm': (u'4D', 48),
            '.': (u'0E', 18), 'N': (u'2E', 37), 'n': (u'4E', 32),
            '/': (u'0F', 23), 'O': (u'2F', 40), 'o': (u'4F', 31),
            '0': (u'10', 32), 'P': (u'30', 30), 'p': (u'50', 30),
            '1': (u'11', 32), 'Q': (u'31', 39), 'q': (u'51', 32),
            '2': (u'12', 32), 'R': (u'32', 35), 'r': (u'52', 21),
            '3': (u'13', 32), 'S': (u'33', 34), 's': (u'53', 26),
            '4': (u'14', 32), 'T': (u'34', 31), 't': (u'54', 20),
            '5': (u'15', 32), 'U': (u'35', 37), 'u': (u'55', 31),
            '6': (u'16', 32), 'V': (u'36', 34), 'v': (u'56', 30),
            '7': (u'17', 32), 'W': (u'37', 49), 'w': (u'57', 41),
            '8': (u'18', 32), 'X': (u'38', 34), 'x': (u'58', 29),
            '9': (u'19', 32), 'Y': (u'39', 31), 'y': (u'59', 30),
            ':': (u'1A', 23), 'Z': (u'3A', 34), 'z': (u'5A', 26),
            ';': (u'1B', 23), '[': (u'3B', 23), '{': (u'5B', 32),
            '<': (u'1C', 41), '\\':(u'3C', 23), '|': (u'5C', 23),
            '=': (u'1D', 41), ']': (u'3D', 23), '}': (u'5D', 32),
            '>': (u'1E', 41), '^': (u'3E', 40), '~': (u'5E', 41),
            '?': (u'1F', 27), '_': (u'3F', 32),
            '@': (u'20', 50), '`': (u'40', 32), 
            'À': (u'82', 34),
            'Á': (u'81', 35),
            'Â': (u'83', 34),
            'Ã': (u'86', 34),
            'Ä': (u'85', 34),
            'Å': (u'84', 34),
            'Ç': (u'87', 35),
            'È': (u'8A', 31),
            'É': (u'89', 32),
            'Ê': (u'8B', 32),
            'Ë': (u'8C', 32),
            'Í': (u'8D', 21),
            'Î': (u'8E', 21),
            'Ï': (u'8F', 21),
            'Ð': (u'88', 39),
            'Ł': (u'9E', 27),
            'Ñ': (u'90', 37),
            'Ò': (u'92', 40),
            'Ó': (u'91', 39),
            'Ô': (u'93', 39),
            'Õ': (u'95', 39),
            'Ö': (u'94', 40),
            '×': (u'60', 26),
            'Ø': (u'96', 39),
            'Ù': (u'98', 36),
            'Ú': (u'97', 37),
            'Û': (u'99', 37),
            'Ü': (u'9A', 37),
            'Ý': (u'9B', 30),
            'à': (u'62', 30),
            'á': (u'61', 30),
            'â': (u'63', 30),
            'ã': (u'66', 30),
            'ä': (u'65', 30),
            'å': (u'64', 30),
            'ç': (u'67', 26),
            'è': (u'6A', 30),
            'é': (u'69', 30),
            'ê': (u'6B', 30),
            'ë': (u'6C', 29),
            'í': (u'6D', 12),
            'î': (u'6E', 12),
            'ï': (u'6F', 12),
            'ł': (u'7E', 15),
            'ð': (u'68', 31),
            'ñ': (u'70', 32),
            'ò': (u'72', 30),
            'ó': (u'71', 30),
            'ô': (u'73', 30),
            'õ': (u'75', 30),
            'ö': (u'74', 31),
            'ø': (u'76', 30),
            'ù': (u'78', 31),
            'ú': (u'77', 32),
            'û': (u'79', 32),
            'ü': (u'7A', 32),
            'ý': (u'7B', 29),
            'ÿ': (u'7C', 30),
            'Č': (u'9F', 35),
            'č': (u'7F', 26),
            'Ń': (u'9D', 38),
            'ń': (u'7D', 31),
            'Š': (u'A0', 35),
            'š': (u'80', 26),
            'Ÿ': (u'9C', 31),
        },
    }

    @classmethod
    def add_text(cls, x, y, s, style, size, align=0, maxwidth=None):
        s = (s or '').replace(u'\u200b', '')
        glyphs = ['<']
        widths = ['[']
        totalwidth = 0
        qmark = cls.font[style]['?']
        for i in s or []:
            glyph_def = cls.font[style].get(i, qmark)
            glyphs.append(glyph_def[0])
            w = (0.28 * glyph_def[1]) * size + 0.5
            totalwidth += w
            widths.append(str(w))
        glyphs.append('>')
        widths.append(']')
        result = []
        squeeze = False
        if maxwidth is not None and totalwidth > maxwidth:
            squeeze = True
            result = ['gsave']
        x -= totalwidth * align
        result.append("%s %s moveto" % (x, y))
        if squeeze:
            result.append('%s 1 scale' % (1.0 * maxwidth / totalwidth))
        result.append("%s\n%s\nxshow" % (''.join(glyphs), ' '.join(widths)))
        if squeeze:
            result.append('grestore')
        return '\n'.join(result)

    @classmethod
    def add_qr(cls, x, y, text, scale=1, side=None):
        return add_qr(x, y, text, scale, side, format='ps')


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
        logger.debug("qr-svg: %s(%s)" % (type(result).__name__, result))
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
