# -*- coding: utf-8 -*-
#
# Copyright 2017 Mario Frasca <mario@anche.no>.
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

class Code39:
    MAP = {' ': u'bWBwbwBwb',
           '$': u'bWbWbWbwb',
           '%': u'bwbWbWbWb',
           '+': u'bWbwbWbWb',
           '-': u'bWbwbwBwB',
           '.': u'BWbwbwBwb',
           '/': u'bWbWbwbWb',
           '0': u'bwbWBwBwb',
           '1': u'BwbWbwbwB',
           '2': u'bwBWbwbwB',
           '3': u'BwBWbwbwb',
           '4': u'bwbWBwbwB',
           '5': u'BwbWBwbwb',
           '6': u'bwBWBwbwb',
           '7': u'bwbWbwBwB',
           '8': u'BwbWbwBwb',
           '9': u'bwBWbwBwb',
           'A': u'BwbwbWbwB',
           'B': u'bwBwbWbwB',
           'C': u'BwBwbWbwb',
           'D': u'bwbwBWbwB',
           'E': u'BwbwBWbwb',
           'F': u'bwBwBWbwb',
           'G': u'bwbwbWBwB',
           'H': u'BwbwbWBwb',
           'I': u'bwBwbWBwb',
           'J': u'bwbwBWBwb',
           'K': u'BwbwbwbWB',
           'L': u'bwBwbwbWB',
           'M': u'BwBwbwbWb',
           'N': u'bwbwBwbWB',
           'O': u'BwbwBwbWb',
           'P': u'bwBwBwbWb',
           'Q': u'bwbwbwBWB',
           'R': u'BwbwbwBWb',
           'S': u'bwBwbwBWb',
           'T': u'bwbwBwBWb',
           'U': u'BWbwbwbwB',
           'V': u'bWBwbwbwB',
           'W': u'BWBwbwbwb',
           'X': u'bWbwBwbwB',
           'Y': u'BWbwBwbwb',
           'Z': u'bWBwBwbwb',
           '!': u'bWbwBwBwb',}

    MAP = {' ': u'█   ███ ███ █ █',
           '$': u'█   █   █   █ █',
           '%': u'█ █   █   █   █',
           '+': u'█   █ █   █   █',
           '-': u'█   █ █ ███ ███',
           '/': u'█   █   █ █   █',
           '.': u'███   █ █ ███ █',
           '0': u'█ █   ███ ███ █',
           '1': u'███ █   █ █ ███',
           '2': u'█ ███   █ █ ███',
           '3': u'███ ███   █ █ █',
           '4': u'█ █   ███ █ ███',
           '5': u'███ █   ███ █ █',
           '6': u'█ ███   ███ █ █',
           '7': u'█ █   █ ███ ███',
           '8': u'███ █   █ ███ █',
           '9': u'█ ███   █ ███ █',
           'A': u'███ █ █   █ ███',
           'B': u'█ ███ █   █ ███',
           'C': u'███ ███ █   █ █',
           'D': u'█ █ ███   █ ███',
           'E': u'███ █ ███   █ █',
           'F': u'█ ███ ███   █ █',
           'G': u'█ █ █   ███ ███',
           'H': u'███ █ █   ███ █',
           'I': u'█ ███ █   ███ █',
           'J': u'█ █ ███   ███ █',
           'K': u'███ █ █ █   ███',
           'L': u'█ ███ █ █   ███',
           'M': u'███ ███ █ █   █',
           'N': u'█ █ ███ █   ███',
           'O': u'███ █ ███ █   █',
           'P': u'█ ███ ███ █   █',
           'Q': u'█ █ █ ███   ███',
           'R': u'███ █ █ ███   █',
           'S': u'█ ███ █ ███   █',
           'T': u'█ █ ███ ███   █',
           'U': u'███   █ █ █ ███',
           'V': u'█   ███ █ █ ███',
           'W': u'███   ███ █ █ █',
           'X': u'█   █ ███ █ ███',
           'Y': u'███   █ ███ █ █',
           'Z': u'█   ███ ███ █ █',
           '!': u'█   █ ███ ███ █',}
