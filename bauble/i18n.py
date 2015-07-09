# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
#
# This file is part of bauble.classic.
#
# bauble.classic is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# bauble.classic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with bauble.classic. If not, see <http://www.gnu.org/licenses/>.
#
# i18n.py
#
# internationalization support
#

"""
The i18n module defines the _() function for creating translatable strings.

_() is added to the Python builtins so there is no reason to import
this module more than once in an application.  It is usually imported
in :mod:`bauble`
"""

import os
import locale
import gettext
import bauble.paths as paths
from bauble import version_tuple

# the following has effect on Windows: to set the environment variables as
# on an operating system. operating systems don't need it.
import bauble.gettext_windows
bauble.gettext_windows.setup_env()

__all__ = ["_"]

TEXT_DOMAIN = 'bauble-%s' % '.'.join(version_tuple[0:2])

#
# most of the following code was adapted from:
# http://www.learningpython.com/2006/12/03/\
# translating-your-pythonpygtk-application/

langs = []
#Check the default locale
lang_code, encoding = locale.getdefaultlocale()
if lang_code:
    # If we have a default, it's the first in the list
    langs = [lang_code]
# Now lets get all of the supported languages on the system
language = os.environ.get('LANGUAGE', None)
if language:
    # langage comes back something like en_CA:en_US:en_GB:en on linuxy
    # systems, on Win32 it's nothing, so we need to split it up into a
    # list
    langs += language.split(":")
# add on to the back of the list the translations that we know that we
# have, our defaults"""
langs += ["en"]

# langs is a list of all of the languages that we are going to try to
# use.  First we check the default, then what the system told us, and
# finally the 'known' list

gettext.bindtextdomain(TEXT_DOMAIN, paths.locale_dir())
gettext.textdomain(TEXT_DOMAIN)
# Get the language to use
lang = gettext.translation(TEXT_DOMAIN, paths.locale_dir(), languages=langs,
                           fallback=True)
# install the language, map _() (which we marked our strings to
# translate with) to self.lang.gettext() which will translate them.
_ = gettext.gettext

# register the gettext function for the whole interpreter as "_"
import __builtin__
__builtin__._ = gettext.gettext
