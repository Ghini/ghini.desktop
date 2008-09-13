#
# i18n.py
#
# internationalization support
#

import sys
import os
import locale
import gettext

__all__ = ["_", '_locale_dir']

def _locale_dir():
    """
    Returns the root path of the locale files
    """
    if sys.platform == 'linux2':
        return os.path.join('/usr', 'share', 'locale')
    elif sys.platform == 'win32':
        return os.path.join(main_dir(), 'locale')
    else:
        raise NotImplementedError('This platform does not support '\
                                  'translations')

APP_NAME = 'bauble'

#
# most of the following code was adapted from:
# http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/

langs = []
#Check the default locale
lc, encoding = locale.getdefaultlocale()
if (lc):
    # If we have a default, it's the first in the list
    langs = [lc]
# Now lets get all of the supported languages on the system
language = os.environ.get('LANGUAGE', None)
if (language):
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

gettext.bindtextdomain(APP_NAME, _locale_dir())
gettext.textdomain(APP_NAME)
# Get the language to use
lang = gettext.translation(APP_NAME, _locale_dir(), languages=langs,
                           fallback=True)
# install the language, map _() (which we marked our strings to
# translate with) to self.lang.gettext() which will translate them.
_ = lang.gettext
