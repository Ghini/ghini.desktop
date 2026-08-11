## -*- coding: utf-8 -*-
##
## Copyright 2012-2018 Mario Frasca <mario@anche.no>.
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
## report/mako/
##
## DOMAIN species
##
<%inherit file="base.ps.mako"/>
<%
from bauble.plugins.report import PS
%>\
/ghini {${PS.insert_picture(22,172,90,120,'tortuosa.jpg')}} def
% for p, v in enumerate(values):
<%text>%%Page: </%text>${p} ${p}
<%text>%%PageOrientation: Portrait
%%PageBoundingBox: 18 18 180 300
%%BeginPageSetup
%
%%EndPageSetup
</%text>
ghini
gsave
[0.24 0 0 -0.24 18 300] concat
gsave
(VerdanaFID313HGSet2) cvn findfont 60 -60 matrix scale makefont setfont
${PS.add_text(60, 1060, v.default_vernacular_name and v.default_vernacular_name.name or '', 'sans', 1.0)}
${PS.add_text(250, 360, v.genus.family.epithet, 'sans', 4, stretch=2.4, maxwidth=390)}
(Verdana-ItalicFID315HGSet2) cvn findfont 120 -120 matrix scale makefont setfont
${PS.add_text(40, 830, v.genus.epithet, 'sans', 8.2, stretch=1.2, maxwidth=590)}
${PS.add_text(40, 950, v.epithet, 'sans', 8.2, stretch=1.2, maxwidth=590)}
(VerdanaFID313HGSet2) cvn findfont 70 -70 matrix scale makefont setfont
${PS.add_text(620, 1040, v.author, 'sans', 5, True, maxwidth=560)}
grestore
showpage
<%text filter="h">
%%PageTrailer
</%text>
% endfor
<%text filter="h">
%%Trailer
%%BoundingBox: 0 0 340 198
%%Orientation: Landscape
%%Pages: </%text>${p}<%text>
%%EOF
</%text>
