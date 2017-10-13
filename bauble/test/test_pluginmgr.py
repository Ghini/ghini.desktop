# -*- coding: utf-8 -*-
#
# Copyright (c) 2005,2006,2007,2008,2009 Brett Adams <brett@belizebotanic.org>
# Copyright (c) 2012-2015 Mario Frasca <mario@anche.no>
# Copyright 2017 Jardín Botánico de Quito
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
# test_pluginmgr.py
#
import os

import unittest

import logging
logger = logging.getLogger(__name__)

#from pyparsing import *
#from sqlalchemy import *
#from bauble.view import SearchView
#from bauble.search import SearchParser, MapperSearch

import bauble
import bauble.db as db
from bauble.test import BaubleTestCase, uri
import bauble.pluginmgr as pluginmgr
from bauble.pluginmgr import PluginRegistry
from bauble.error import BaubleError
import bauble.utils as utils


class A(pluginmgr.Plugin):
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class B(pluginmgr.Plugin):
    depends = ['A']
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class C(pluginmgr.Plugin):
    depends = ['B']
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        assert A.initialized and B.initialized
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class FailingInitPlugin(pluginmgr.Plugin):
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True
        raise BaubleError("can't init")

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class DependsOnFailingInitPlugin(pluginmgr.Plugin):
    depends = ['FailingInitPlugin']
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class FailingInstallPlugin(pluginmgr.Plugin):
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True
        raise BaubleError("can't install")


class DependsOnFailingInstallPlugin(pluginmgr.Plugin):
    depends = ['FailingInstallPlugin']
    initialized = False
    installed = False

    @classmethod
    def init(cls):
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs):
        cls.installed = True


class PluginMgrTests(BaubleTestCase):

    def test_install(self):
        """
        Test importing default data from plugin
        """
        # this emulates the PlantsPlugin install() method but only
        # imports the family.txt file...if PlantsPlugin.install()
        # changes we should change this method as well
        class Dummy(pluginmgr.Plugin):
            @classmethod
            def init(cls):
                pass

            @classmethod
            def install(cls, import_defaults=True):
                import bauble.paths as paths
                if not import_defaults:
                    return
                path = os.path.join(paths.lib_dir(), "plugins", "plants",
                                    "default")
                filenames = os.path.join(path, 'family.txt')
                from bauble.plugins.imex.csv_ import CSVImporter
                csv = CSVImporter()
                try:
                    csv.start([filenames], metadata=db.metadata,
                              force=True)
                except Exception, e:
                    logger.error(e)
                    raise
                from bauble.plugins.plants import Family
                self.assertEquals(self.session.query(Family).count(), 1387)
        pluginmgr.plugins[Dummy.__name__] = Dummy
        pluginmgr.install([Dummy])


class LocalFunctions(unittest.TestCase):
    def setUp(self):
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False
        bauble.pluginmgr.plugins = {}

    def tearDown(self):
        bauble.pluginmgr.plugins = {}

    def test_create_dependency_pairs(self):
        a, b, c = A(), B(), C()
        a.__name__ = 'A'
        b.__name__ = 'B'
        c.__name__ = 'C'
        bauble.pluginmgr.plugins[C.__name__] = c
        bauble.pluginmgr.plugins[B.__name__] = b
        bauble.pluginmgr.plugins[A.__name__] = a
        dep, unmet = bauble.pluginmgr._create_dependency_pairs([a, b, c])
        self.assertEquals(dep, [(a, b), (b, c)])
        self.assertEquals(unmet, {})

    def test_create_dependency_pairs_missing_base(self):
        a, b, c = A(), B(), C()
        a.__name__ = 'A'
        b.__name__ = 'B'
        c.__name__ = 'C'
        bauble.pluginmgr.plugins[C.__name__] = c
        bauble.pluginmgr.plugins[B.__name__] = b
        dep, unmet = bauble.pluginmgr._create_dependency_pairs([b, c])
        self.assertEquals(dep, [(b, c)])
        self.assertEquals(unmet, {'B': ['A']})


class StandalonePluginMgrTests(unittest.TestCase):

    def setUp(self):
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False
        bauble.pluginmgr.plugins = {}

    def tearDown(self):
        for z in [A, B, C]:
            z.initialized = z.installed = False

    def test_command_handler(self):
        """
        Test that the command handlers get properly registered...this
        could probably just be included in test_init()
        """
        pass

    def test_successfulinit(self):
        "bauble.pluginmgr.init() should be successful"

        db.open(uri, verify=False)
        db.create(False)
        bauble.pluginmgr.plugins[C.__name__] = C()
        bauble.pluginmgr.plugins[B.__name__] = B()
        bauble.pluginmgr.plugins[A.__name__] = A()
        bauble.pluginmgr.init(force=True)
        self.assertTrue(A.initialized)
        self.assertTrue(B.initialized)
        self.assertTrue(C.initialized)

    def test_init_with_problem(self):
        "bauble.pluginmgr.init() using plugin which can't initialize"

        old_dialog = utils.message_details_dialog
        self.invoked = False

        def fake_dialog(a, b, c):
            "trap dialog box invocation"
            self.invoked = True

        utils.message_details_dialog = fake_dialog

        db.open(uri, verify=False)
        db.create(False)
        bauble.pluginmgr.plugins[
            FailingInitPlugin.__name__] = FailingInitPlugin()
        bauble.pluginmgr.plugins[
            DependsOnFailingInitPlugin.__name__] = DependsOnFailingInitPlugin()
        bauble.pluginmgr.init(force=True)
        self.assertTrue(self.invoked)
        self.assertFalse(DependsOnFailingInitPlugin.initialized)
        utils.message_details_dialog = old_dialog

    def test_install_with_problem(self):
        "bauble.pluginmgr.init() using plugin which can't install"

        db.open(uri, verify=False)
        db.create(False)
        bauble.pluginmgr.plugins[
            FailingInstallPlugin.__name__] = FailingInstallPlugin()
        bauble.pluginmgr.plugins[
            DependsOnFailingInstallPlugin.__name__
            ] = DependsOnFailingInstallPlugin()
        self.assertRaises(BaubleError, bauble.pluginmgr.init, force=True)

    def test_install(self):
        """
        Test bauble.pluginmgr.install()
        """

        pA = A()
        pB = B()
        pC = C()
        bauble.pluginmgr.plugins[C.__name__] = pC
        bauble.pluginmgr.plugins[B.__name__] = pB
        bauble.pluginmgr.plugins[A.__name__] = pA
        db.open(uri, verify=False)
        db.create(False)
        bauble.pluginmgr.install((pA, pB, pC), force=True)
        self.assert_(A.installed and B.installed and C.installed)

    def test_dependencies_BA(self):
        "test that loading B will also load A but not C"

        pA = A()
        pB = B()
        pC = C()
        bauble.pluginmgr.plugins[B.__name__] = pB
        bauble.pluginmgr.plugins[A.__name__] = pA
        bauble.pluginmgr.plugins[C.__name__] = pC
        self.assertFalse(C.installed)
        self.assertFalse(B.installed)
        self.assertFalse(A.installed)
        db.open(uri, verify=False)
        db.create(False)
        # the creation of the database installed all plugins, so we manually
        # reset everything, just to make sure we really test the logic
        C.installed = B.installed = A.installed = False
        ## should try to load the A plugin
        bauble.pluginmgr.install((pB, ), force=True)
        self.assertTrue(B.installed)
        self.assertTrue(A.installed)
        # self.assertFalse(C.installed)

    def test_dependencies_CBA(self):
        "test that loading C will load B and consequently A"

        pA = A()
        pB = B()
        pC = C()
        bauble.pluginmgr.plugins[B.__name__] = pB
        bauble.pluginmgr.plugins[A.__name__] = pA
        bauble.pluginmgr.plugins[C.__name__] = pC
        self.assertFalse(C.installed)
        self.assertFalse(B.installed)
        self.assertFalse(A.installed)
        db.open(uri, verify=False)
        db.create(False)
        # the creation of the database installed all plugins, so we manually
        # reset everything, just to make sure we really test the logic
        C.installed = B.installed = A.installed = False
        ## should try to load the A plugin
        bauble.pluginmgr.install((pC, ), force=True)
        self.assertTrue(C.installed)
        self.assertTrue(B.installed)
        self.assertTrue(A.installed)


class PluginRegistryTests(BaubleTestCase):

    def test_registry(self):
        """
        Test bauble.pluginmgr.PluginRegistry
        """

        ## this is the plugin object
        p = A()

        # test that adding works
        PluginRegistry.add(p)
        self.assert_(PluginRegistry.exists(p))

        # test that removing works
        PluginRegistry.remove(p)
        self.assert_(not PluginRegistry.exists(p))
