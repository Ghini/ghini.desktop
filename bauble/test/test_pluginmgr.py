#
# test_pluginmgr.py
#
import os
import sys
import unittest

from pyparsing import *
from sqlalchemy import *

import bauble
import bauble.db as db
from bauble.search import SearchParser, MapperSearch
from bauble.view import SearchView
from bauble.utils.log import debug, error
from bauble.test import BaubleTestCase, uri
import bauble.pluginmgr as pluginmgr
from bauble.pluginmgr import PluginRegistry


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
                    error(e)
                    raise
                from bauble.plugins.plants import Family
                self.assert_(self.session.query(Family).count() == 511)
        pluginmgr.plugins[Dummy.__name__] = Dummy
        pluginmgr.install([Dummy])


class StandalonePluginMgrTests(unittest.TestCase):

    def setUp(self):
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False

    def tearDown(self):
        for z in [A, B, C]:
            z.initialized = z.installed = False

    def test_command_handler(self):
        """
        Test that the command handlers get properly registered...this
        could probably just be included in test_init()
        """
        pass

    def test_init(self):
        """
        Test bauble.pluginmgr.init()
        """
        db.open(uri, verify=False)
        db.create(False)
        bauble.pluginmgr.plugins[C.__name__] = C()
        bauble.pluginmgr.plugins[B.__name__] = B()
        bauble.pluginmgr.plugins[A.__name__] = A()
        bauble.pluginmgr.init(force=True)
        self.assert_(A.initialized and B.initialized and C.initialized)

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
        "test that loading B will also load A"

        pA = A()
        pB = B()
        pC = C()
        bauble.pluginmgr.plugins[B.__name__] = pB
        bauble.pluginmgr.plugins[A.__name__] = pA
        bauble.pluginmgr.plugins[C.__name__] = pC
        db.open(uri, verify=False)
        db.create(False)
        ## should try to load the A plugin
        self.assertRaises(KeyError, bauble.pluginmgr.install, (pB, ), force=True)

    def test_dependencies_CA(self):
        "test that loading C will also load A"

        pA = A()
        pB = B()
        pC = C()
        bauble.pluginmgr.plugins[B.__name__] = pB
        bauble.pluginmgr.plugins[A.__name__] = pA
        bauble.pluginmgr.plugins[C.__name__] = pC
        db.open(uri, verify=False)
        db.create(False)
        ## should try to load the A plugin
        self.assertRaises(KeyError, bauble.pluginmgr.install, (pC, ), force=True)


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
