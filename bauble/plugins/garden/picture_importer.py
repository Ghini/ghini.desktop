# -*- coding: utf-8 -*-
#
# Copyright 2018 Mario Frasca <mario@anche.no>.
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


import re

def decode_parts(name):
    """return the dictionary of parts in name according to pattern.

    pattern is a string, containing elements like {name}, while the rest of
    the string is considered literally.  the name is matched against the
    pattern.  if it matches, a dictionary is constructed and returned, if it
    does not match, None is returned, if an invalid pattern is given, an
    exception is raised.

    names of parts have to be selected from a hard coded set, where also the
    defaults are hard coded.

    accession, compulsory, no default possible,
    plant, optional, defaults to 1,
    seq, optional, defaults to 1,
    species, optional, defaults to Zzz

    matching is case-insensitive.  a leading original picture name (a
    sequence of letters plus a sequence of numbers) can be used to define
    the picture sequential number.

    """

    # remove the extension

    # look for anything looking like (and remove it), in turn: species name,
    # accession number with optional plant number, original picture name,
    # some other number overruling the original picture name.

    result = {'accession': None,
              'plant': '1',
              'seq': '1',
              'species': 'Zzz'}

    for key, exp in [('species', r'([A-Z][a-z]+(?: [a-z-]*)?)'),
                     ('accession', r'([12][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9])(:?\.([0-9]+))?'),
                     ('seq', r'([A-Z]+[0-9]+)'),
                     ('seq', r'([0-9]+)')]:
        match = re.search(exp, name)
        if match:
            value = match.group(1)
            if not value:
                continue
            if key == 'seq':
                value = re.sub(r'([A-Z]+0*)', '', value)
            result[key] = value
            if key == 'accession' and match.group(2):
                result['plant'] = match.groups()[2]
            print name, ':::', 
            name = name.replace(match.group(0), '')
        print name
    if result['accession'] is None:
        return None
    return result
