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
        return os.path.join('usr', 'share', 'locale')
    elif sys.platform == 'win32':
        return os.path.join(main_dir(), 'locale')
    else:
        raise NotImplementedError('This platform does not support '\
                                  'translations')

APP_NAME = 'bauble'
locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain(APP_NAME, _locale_dir())
gettext.textdomain(APP_NAME)
f = gettext.find(APP_NAME)#, _locale_dir())
print f
# glade internationalization is setup in bauble/__init__.py after gtk
# is successfully imported
_ = gettext.gettext
