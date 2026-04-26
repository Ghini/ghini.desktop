#!/usr/bin/env python
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2015 Mario Frasca <mario@anche.no>
# Copyright (c) 2016,2017 Ross Demuth <rossdemuth123@gmail.com>
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

import sys
import shutil
import subprocess
import setuptools
from setuptools import Command
from setuptools.command.build import build as _build
from setuptools.command.install import install as _install
import os
import glob

# Shared vars
LOCALE_PATH = os.path.join("share", "locale")

# --- Custom Build Commands ---

class build(_build):
    def run(self):
        if not shutil.which("msgfmt"):
            sys.exit("**Error: gettext 'msgfmt' not found.")
        os.makedirs(os.path.join(self.build_base, "share", "ghini"), exist_ok=True)
        super().run()
        self.build_locales()
        self.build_icons()

    def build_locales(self):
        dest = os.path.join(self.build_base, LOCALE_PATH, "%s", "LC_MESSAGES")
        for po in glob.glob("po/*.po"):
            lang = os.path.splitext(os.path.basename(po))[0]
            localedir = dest % lang
            mo = f"{localedir}/ghini.mo"
            os.makedirs(localedir, exist_ok=True)
            subprocess.run(["msgfmt", po, "-o", mo], check=True)

    def build_icons(self):
        if sys.platform == "linux":
            base = self.build_base
            icons_path = os.path.join(base, "share", "icons", "hicolor")
            sizes = [16, 22, 24, 32, 48, 64]
            for size in sizes:
                icon_src = f"data/ghini-{size}.png"
                icon_dest = os.path.join(icons_path, f"{size}x{size}", "apps", "ghini.png")
                os.makedirs(os.path.dirname(icon_dest), exist_ok=True)
                shutil.copy2(icon_src, icon_dest)
            shutil.copy2("data/ghini.svg", os.path.join(base, "share/pixmaps"))

class install(_install):
    def run(self):
        if sys.platform not in ("linux", "win32", "darwin"):
            sys.exit(f"Unsupported platform: {sys.platform}")
        super().run()
        shutil.copytree(os.path.join(self.build_base, "share"),
                        os.path.join(self.install_data, "share"),
                        dirs_exist_ok=True)
        shutil.copy2("LICENSE", os.path.join(self.install_data, "share", "ghini"))

class docs(Command):
    user_options = [("all", "a", "rebuild all docs")]
    def initialize_options(self): self.all = False
    def finalize_options(self): pass
    def run(self):
        subprocess.run(["sphinx-build", "-b", "html",
                        "doc", "doc/.build"] + (["-E"] if self.all else []), check=True)

class clean(Command):
    user_options = [("all", "a", "clean all artifacts")]
    def initialize_options(self): self.all = False
    def finalize_options(self): pass
    def run(self):
        dirs = ["dist", "build", "deb_dist", "doc/.build", "*.egg-info"]
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)

class run(Command):
    user_options = []
    def initialize_options(self): pass
    def finalize_options(self): pass
    def run(self):
        subprocess.run(["./ghini.sh"], check=True)

# Windows-only commands
if sys.platform == "win32":
    class py2exe_cmd(Command):
        description = "build standalone Windows executable"
        user_options = []
        def initialize_options(self): pass
        def finalize_options(self): pass
        def run(self):
            subprocess.run(["py2exe", "scripts/ghini"], check=True)

    class nsis_cmd(Command):
        description = "build NSIS installer"
        user_options = [("makensis=", None, "path to makensis")]
        def initialize_options(self): self.makensis = "makensis"
        def finalize_options(self): pass
        def run(self):
            subprocess.run([self.makensis, "scripts/build-multiuser.nsi"], check=True)
else:
    py2exe_cmd = nsis_cmd = type("Unsupported", (Command,), {
        "user_options": [], 
        "run": lambda self: sys.exit("Not supported on this platform.")
    })

setuptools.setup(
    use_scm_version=True,
    setup_requires=["setuptools>=65.5", "setuptools-scm"],
    cmdclass={
        "build": build,
        "install": install,
        "docs": docs,
        "clean": clean,
        "run": run,
        "py2exe": py2exe_cmd,
        "nsis": nsis_cmd,
    },
)