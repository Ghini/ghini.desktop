## -*- coding: utf-8 -*-
##
## Copyright 2015-2017 Mario Frasca <mario@anche.no>.
##
## This file is part of ghini.desktop.
##
## ghini.desktop is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## ghini.desktop is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with ghini.desktop. If not, see <http://www.gnu.org/licenses/>.
##
## DOMAIN plant
##
## OPTION extra_text: (type: string, default: '', tooltip: 'print this on the second text line.')
## OPTION accession_format: (type: string, default: '', tooltip: 'ignore selection and print a range.')
## OPTION accession_first: (type: integer, default: '', tooltip: 'start of range.')
## OPTION accession_last: (type: integer, default: '', tooltip: 'end of range.')
##
<%inherit file="base.ps.mako"/>
/SCALE { 0.45 0.45 scale 0 30 translate } bind def
<%
from bauble.plugins.report import options
from bauble.plugins.report import add_qr
page = 1

if options['accession_format']:
    format = options['accession_format']
    start = format.rstrip('#')
    if start != format:
        digits = len(format) - len(start)
        format = start + '%%0%dd' % digits
    first = int(options['accession_first'])
    enumeration = [(i - first, format % i, None) for i in range(first, int(options['accession_last']) + 1)]
else:
    enumeration = [(i, p.accession.code + (p.code != '1' and '.' + p.code or ''), p.accession) for (i, p) in enumerate(values)]

# `enumeration` is an iterable with tuple elements like (i, code, obj),
# where: i are sequential and start at 0; code is the plant code; obj may be
# the accession associated to the plant

%>
% for page, plant_code, accession in enumeration:
<%text>%%Page: </%text>${page} ${page}<%text>
%%BeginPageSetup
%%PageBoundingBox:  0 0 144 72
%%EndPageSetup
grestore
</%text>\
<%
et = options['extra_text']
if et:
  if accession and et.startswith('{') and et.endswith('}'):
    ets = accession
    for step in et[1:-1].split('.'):
      ets = getattr(ets, step)
    et = str(ets)
  genus_epithet = et
  species_epithet = ''
else:
  if accession is None:
    genus_epithet = species_epithet = ''
  else:
    genus_epithet = accession.species.genus.epithet
    if genus_epithet.startswith('Zzz'):
      genus_epithet = ''
    elif genus_epithet.startswith('Zzx-'):
      genus_epithet = genus_epithet[4:]
    species_epithet = accession.species.epithet
    if species_epithet == 'sp':
      species_epithet = ''
%>
gsave
SCALE
0 0 0 setrgbcolor
0.4 setlinewidth 
newpath 0 0 moveto 8 0 rlineto stroke
newpath 0 0 moveto 0 8 rlineto stroke
newpath 320 100 moveto -8 0 rlineto stroke
newpath 320 100 moveto 0 -8 rlineto stroke
newpath 0 100 moveto 8 0 rlineto stroke
newpath 0 100 moveto 0 -8 rlineto stroke
newpath 320 0 moveto -8 0 rlineto stroke
newpath 320 0 moveto 0 8 rlineto stroke
1 setlinewidth
${add_qr(230, 10, plant_code, side=80.0, format='ps')}
(VerdanaFID313HGSet2) cvn findfont 40 40 matrix scale makefont setfont
${add_text(8, 53, plant_code, 'sans', 2.6, align=0, maxwidth=212)}
(Verdana-ItalicFID315HGSet2) cvn findfont 20 20 matrix scale makefont setfont
${add_text(8, 28, genus_epithet, 'sans', 1.3)}
${add_text(8, 8, species_epithet, 'sans', 1.3)}
grestore
grestore
<%text filter="h">
showpage
%%PageTrailer
</%text>
% endfor
<%text filter="h">
%%Trailer
%%Pages: </%text>${page}<%text>
%%EOF
</%text>\
