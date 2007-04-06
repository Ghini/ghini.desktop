#
# i18n.py
#
# internationalization support
#

import locale
import gettext
import bauble.paths as paths

__all__ = ["_"]

locale.setlocale(locale.LC_ALL, '')
gettext.bindtextdomain('bauble', paths.locale_dir())
gettext.textdomain('bauble')
_ = gettext.gettext
