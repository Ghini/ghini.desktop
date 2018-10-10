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
## DOMAIN species
##
<%
%>Generic Hybrid Symbol,Generic Epithet,Specific Hybrid Symbol,Specific Epithet,Infraspecific Rank,Infraspecific Epithet,Cultivar Epithet
% for v in values:
<%
    genus = v.genus.genus
    if genus.startswith('Zzz-'):
        genus = ''
    species_epithet = v.sp
    if (species_epithet or '').startswith('sp'):
        species_epithet = ''
    hybrid_marker = ''
    if '×' in v.sp:
        hybrid_marker = 'H'
    if '×' in v.sp[:1]:
        hybrid_marker = '×'
        species_epithet = species_epithet[1:]
%>${v.genus.hybrid_marker},${v.genus.epithet},${hybrid_marker},${species_epithet},${v.infraspecific_rank or ''},${v.infraspecific_epithet or ''},${v.cultivar_epithet or ''}
% endfor
