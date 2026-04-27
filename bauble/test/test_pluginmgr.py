import logging
import os
from collections.abc import Generator
from typing import Any

import pytest
from bauble import db
from bauble.error import BaubleError
from bauble.pluginmgr import Plugin as Plugin
from bauble.pluginmgr import PluginRegistry as PluginRegistry
from bauble.pluginmgr import _create_dependency_pairs as _create_dependency_pairs
from bauble.pluginmgr import init as init
from bauble.pluginmgr import install as install
from bauble.pluginmgr import plugins as plugins

logger: Any = logging.getLogger(__name__)


class A(Plugin):
    depends: Any = []
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class B(Plugin):
    depends: Any = ["A"]
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class C(Plugin):
    depends: Any = ["B"]
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        assert A.initialized and B.initialized
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class FailingInitPlugin(Plugin):
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True
        raise BaubleError("can't init")

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class DependsOnFailingInitPlugin(Plugin):
    depends: Any = ["FailingInitPlugin"]
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class FailingInstallPlugin(Plugin):
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True
        raise BaubleError("can't install")


class DependsOnFailingInstallPlugin(Plugin):
    depends: Any = ["FailingInstallPlugin"]
    initialized: bool = False
    installed: bool = False

    @classmethod
    def init(cls) -> None:
        cls.initialized = True

    @classmethod
    def install(cls, *args, **kwargs) -> None:
        cls.installed = True


class PluginMgrTests:
    """
    Pytest-based class for testing plugin manager functionality.
    """

    def test_install(self, db_session, mock_logger) -> None:
        """
        Test importing default data from a plugin.
        """

        # this emulates the PlantsPlugin install() method but only
        # imports the family.txt file...if PlantsPlugin.install()
        # changes we should change this method as well
        class Dummy(Plugin):
            @classmethod
            def init(cls):
                pass

            @classmethod
            def install(cls, import_defaults=True):
                """
                Mimic the PlantsPlugin install method but only import the family.txt file.
                """
                import bauble.paths as paths

                if not import_defaults:
                    return

                # Construct path to family.txt
                path = os.path.join(paths.lib_dir(), "plugins", "plants", "default")
                filenames = os.path.join(path, "family.txt")
                from bauble.plugins.imex.csv_ import CSVImporter

                csv = CSVImporter()

                try:
                    # Start CSV import
                    csv.start([filenames], metadata=db.metadata, force=True)
                except Exception as e:
                    logger.error(e)
                    raise

                # Verify the expected record count
                from bauble.plugins.plants import Family
                from sqlalchemy import func, select

                stmt = select(func.count()).select_from(Family)
                count = db_session.execute(stmt).scalar_one()
                assert count == 1387, f"Expected 1387 records in Family, found {count}"

        # Register and install the plugin
        plugins[Dummy.__name__] = Dummy
        install([Dummy])

        # Ensure the plugin installed successfully
        assert Dummy.installed, "Dummy plugin was not installed successfully."


class LocalFunctions:
    """
    Tests for creating dependency pairs and handling missing dependencies.
    """

    @pytest.fixture(autouse=True)
    def reset_plugins(self) -> Generator[None, None, None]:
        """
        Fixture to reset plugin states and the plugins dictionary before and after each test.
        """
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False
        plugins.clear()
        yield
        plugins.clear()

    def test_create_dependency_pairs(self) -> None:
        """
        Test creating dependency pairs for valid plugins.
        """
        # Create plugin instances
        a, b, c = A(), B(), C()

        # Register plugins
        plugins.update({cls.__name__: cls for cls in [a, b, c]})

        # Generate dependency pairs
        dep, unmet = _create_dependency_pairs([a, b, c])

        # Assert dependencies and unmet dependencies
        assert dep == [(a, b), (b, c)], f"Unexpected dependency pairs: {dep}"
        assert unmet == {}, f"Unexpected unmet dependencies: {unmet}"

    def test_create_dependency_pairs_missing_base(self) -> None:
        """
        Test handling missing base dependencies.
        """
        # Create plugin instances
        b, c = B(), C()

        # Register plugins with a missing base dependency
        plugins.update({cls.__name__: cls for cls in [b, c]})

        # Generate dependency pairs
        dep, unmet = _create_dependency_pairs([b, c])

        # Assert dependencies and unmet dependencies
        assert dep == [(b, c)], f"Unexpected dependency pairs: {dep}"
        assert unmet == {"B": ["A"]}, f"Unexpected unmet dependencies: {unmet}"


class StandalonePluginMgrTests:
    """
    Tests for standalone plugin manager operations.
    """

    @pytest.fixture(autouse=True)
    def reset_plugins(self) -> Generator[None, None, None]:
        """
        Fixture to reset plugin states and the plugins dictionary before and after each test.
        """
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False
        plugins.clear()
        yield
        plugins.clear()

    @pytest.fixture
    def mock_message_dialog(self, monkeypatch):
        """
        Mock the message_details_dialog function to track invocations.
        """
        invoked = {"status": False}

        def fake_dialog(*args, **kwargs):
            invoked["status"] = True

        monkeypatch.setattr("bauble.utils.message_details_dialog", fake_dialog)
        return invoked

    def test_command_handler(self) -> None:
        """
        Placeholder for testing command handlers.
        """
        pass  # No functionality to test here in the original implementation.

    def test_successfulinit(self, db_session) -> None:
        """
        Test that plugin manager initializes successfully with dependencies.
        """
        plugins.update({cls.__name__: cls for cls in [A, B, C]})
        init(force=True)

        assert A.initialized, "Plugin A was not initialized"
        assert B.initialized, "Plugin B was not initialized"
        assert C.initialized, "Plugin C was not initialized"

    def test_init_with_problem(self, db_session, mock_message_dialog) -> None:
        """
        Test plugin manager initialization with a plugin that cannot initialize.
        """
        plugins["FailingInitPlugin"] = FailingInitPlugin()
        plugins["DependsOnFailingInitPlugin"] = DependsOnFailingInitPlugin()

        init(force=True)

        assert mock_message_dialog[
            "status"
        ], "Expected dialog invocation for initialization failure"
        assert (
            not DependsOnFailingInitPlugin.initialized
        ), "DependsOnFailingInitPlugin should not be initialized"

    def test_install_with_problem(self, db_session) -> None:
        """
        Test plugin installation with a plugin that cannot install.
        """
        plugins["FailingInstallPlugin"] = FailingInstallPlugin()
        plugins["DependsOnFailingInstallPlugin"] = DependsOnFailingInstallPlugin()

        with pytest.raises(BaubleError, match="can't install"):
            install(
                [FailingInstallPlugin(), DependsOnFailingInstallPlugin()], force=True
            )

    def test_install(self, db_session) -> None:
        """
        Test plugin installation and verify all plugins are installed correctly.
        """
        pA, pB, pC = A(), B(), C()
        plugins.update({cls.__name__: cls for cls in [pA, pB, pC]})

        install([pA, pB, pC], force=True)

        assert A.installed, "Plugin A was not installed"
        assert B.installed, "Plugin B was not installed"
        assert C.installed, "Plugin C was not installed"

    def test_dependencies_BA(self, db_session) -> None:
        """
        Test that loading B installs A but not C.
        """
        pA, pB, pC = A(), B(), C()
        plugins.update({cls.__name__: cls for cls in [pA, pB, pC]})

        install([pB], force=True)

        assert A.installed, "Plugin A was not installed as dependency of B"
        assert B.installed, "Plugin B was not installed"
        assert not C.installed, "Plugin C should not be installed"

    def test_dependencies_CBA(self, db_session) -> None:
        """
        Test that loading C installs B and A.
        """
        pA, pB, pC = A(), B(), C()
        plugins.update({cls.__name__: cls for cls in [pA, pB, pC]})

        install([pC], force=True)

        assert A.installed, "Plugin A was not installed as dependency of C"
        assert B.installed, "Plugin B was not installed as dependency of C"
        assert C.installed, "Plugin C was not installed"


class PluginRegistryTests:
    """
    Tests for the PluginRegistry functionality.
    """

    @pytest.fixture(autouse=True)
    def reset_plugins(self) -> Generator[None, None, None]:
        """
        Fixture to reset plugin states and the plugins dictionary before and after each test.
        """
        A.initialized = A.installed = False
        B.initialized = B.installed = False
        C.initialized = C.installed = False
        PluginRegistry.clear()  # Clear PluginRegistry if such a method exists
        yield
        PluginRegistry.clear()  # Clear PluginRegistry after the test

    def test_registry(self, db_session) -> None:
        """
        Test the functionality of the PluginRegistry.
        """
        plugin_instance = A()

        # Add the plugin to the registry
        PluginRegistry.add(plugin_instance)
        assert PluginRegistry.exists(
            plugin_instance
        ), "Plugin was not added to the registry"

        # Remove the plugin from the registry
        PluginRegistry.remove(plugin_instance)
        assert not PluginRegistry.exists(
            plugin_instance
        ), "Plugin was not removed from the registry"
