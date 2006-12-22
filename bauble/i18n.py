#
# i18n.py
#
# internationalization support
#

import locale
import gettext
import bauble.paths as paths

__all__ = ["_"]

DIR = paths.lib_dir()
locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain('bauble', DIR)
gettext.textdomain('bauble')
_ = gettext.gettext
