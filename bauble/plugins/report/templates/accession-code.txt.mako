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
## DOMAIN raw
##
old_accessions = set([\
##
% for i, p in enumerate(values):
##
'${p}', \
% if (i % 5) == 4:

                      \
% endif
##
% endfor
])
