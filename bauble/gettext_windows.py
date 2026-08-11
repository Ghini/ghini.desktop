#
# Copyright (c) 2006, 2007, 2010 Alexander Belchenko
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""Helper for standard gettext.py on Windows.

Module obtains user language code on Windows to use with standard
Python gettext.py library.

The module provides 2 functions: setup_env and get_language.

You may use setup_env before initializing gettext functions.

Or you can use get_language to get the list of language codes suitable
to pass them to gettext.find or gettext.translation function.

Usage example #1:

import gettext, gettext_windows
gettext_windows.setup_env()
gettext.install('myapp')

Usage example #2:

import gettext, gettext_windows
lang = gettext_windows.get_language()
translation = gettext.translation('myapp', languages=lang)
_ = translation.gettext
"""
import locale
import os
import sys
from typing import Any, Optional, cast

OS_WINDOWS: Any = sys.platform == "win32"


def setup_env_windows(system_lang: bool = True) -> None:
    """Check environment variables used by gettext
    and setup LANG if there is none.
    """
    if _get_lang_env_var() is not None:
        return
    lang = get_language_windows(system_lang)
    if lang:
        os.environ["LANGUAGE"] = ":".join(lang)


def get_language_windows(system_lang: bool = True) -> Optional[list[str]]:
    """Get language code based on current Windows settings.
    @return: list of languages.
    """
    try:
        import ctypes

        windll = cast(Any, ctypes).windll  # silence mypy on non-Windows
    except (ImportError, AttributeError):
        default_locale = locale.getdefaultlocale()[0]
        return [default_locale] if default_locale is not None else None
    # get all locales using windows API
    lcid_user = windll.kernel32.GetUserDefaultLCID()
    lcid_system = windll.kernel32.GetSystemDefaultLCID()
    lcids = (
        [lcid_user, lcid_system]
        if system_lang and lcid_user != lcid_system
        else [lcid_user]
    )

    langs = [locale.windows_locale[i] for i in lcids if i in locale.windows_locale]
    return langs or None


def setup_env_other(system_lang: bool = True) -> None:
    pass


def get_language_other(system_lang: bool = True) -> Optional[list[str]]:
    lang = _get_lang_env_var()
    if lang is not None:
        return lang.split(":")
    return None


def _get_lang_env_var() -> Optional[str]:
    for i in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        lang = os.environ.get(i)
        if lang:
            return lang
    return None


get_language = get_language_windows
get_language = get_language_other
setup_env = setup_env_windows
setup_env = setup_env_other
if OS_WINDOWS:
    setup_env = setup_env_windows
    get_language = get_language_windows
else:
    setup_env = setup_env_other
    get_language = get_language_other
