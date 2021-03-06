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
%>Family	Genus	Species	Author	CITES	Condition	Conservation	Groups	Plants	Habit
% for v in values:
<%
    genus = v.genus.genus
    if genus.startswith('Zzz-'):
        genus = ''
    species_epithet = v.sp
    if species_epithet == 'sp':
        species_epithet = ''
    cites = v.cites or ''
    group_count = 0
    plant_count = 0
    for a in v.accessions:
        group_count += len(a.plants)
        for p in a.plants:
            plant_count += p.quantity
%>${v.genus.family}	${genus}	${species_epithet}	${v.author or ''}	${v.cites or ''}	${v.condition or ''}	${v.conservation or ''}	${group_count}	${plant_count}	${v.habit or ''}
% endfor
