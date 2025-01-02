"""Tests for config module."""

import inspect
from unittest import TestCase

from simple_config_builder.config import (
    ConfigClassRegistry,
    config_field,
    configclass,
)


class TestConfig(TestCase):
    """Test Config class."""

    def test_config_class_registry_register(self):
        """Test registering a class in ConfigClassRegistry."""

        class A:
            pass

        ConfigClassRegistry.register(A)
        self.assertTrue(
            ConfigClassRegistry.get_class_str_from_class(A)
            in ConfigClassRegistry.list_classes()
        )

    def test_config_class_registry_list_classes(self):
        """
        Test the `list_classes` method of `ConfigClassRegistry`.

        This test ensures that classes registered with `ConfigClassRegistry`
        are correctly listed by the `list_classes` method.

        Steps:
        1. Define two classes, `A` and `B`.
        2. Register both classes with `ConfigClassRegistry`.
        3. Assert that both classes are present in the list
        returned by `list_classes`.
        """

        class B:
            pass

        class C:
            pass

        ConfigClassRegistry.register(B)
        ConfigClassRegistry.register(C)
        self.assertIn(
            ConfigClassRegistry.get_class_str_from_class(B),
            ConfigClassRegistry.list_classes(),
        )
        self.assertIn(
            ConfigClassRegistry.get_class_str_from_class(C),
            ConfigClassRegistry.list_classes(),
        )

    def test_config_class_registry_is_registered(self):
        """
        Test that the ConfigClassRegistry correctly registers.

        This test performs the following checks:
        1. Defines a class A and registers it with ConfigClassRegistry.
        2. Asserts that class A is registered in the ConfigClassRegistry.
        3. Defines a class B without registering it.
        4. Asserts that class B is not registered in the ConfigClassRegistry.
        """

        class D:
            pass

        ConfigClassRegistry.register(D)
        self.assertTrue(ConfigClassRegistry.is_registered(D))

        class E:
            pass

        self.assertFalse(ConfigClassRegistry.is_registered(E))

    def test_config_class_decorator(self):
        """Test the configclass decorator."""

        @configclass
        class F:
            value1: str

        self.assertTrue(
            ConfigClassRegistry.get_class_str_from_class(F)
            in ConfigClassRegistry.list_classes()
        )

    def test_config_class_decorator_config_field(self):
        """Test the config_field decorator."""

        @configclass
        class G:
            value1: str = config_field()

        self.assertTrue(hasattr(G, "value1"))
        self.assertTrue(isinstance(G.value1, property))

    def test_config_class_decorator_config_field_gt(self):
        """Test the config_field decorator with greater than constraint."""

        @configclass
        class H:
            value1: int = config_field(gt=0, default=1)

        c = H()
        c.value1 = 1
        with self.assertRaises(ValueError):
            c.value1 = -1

    def test_config_class_decorator_config_field_lt(self):
        """Test the config_field decorator with less than constraint."""

        @configclass
        class Il:
            value1: int = config_field(lt=0, default=-1)

        c = Il()
        c.value1 = -1
        with self.assertRaises(ValueError):
            c.value1 = 1

    def test_config_class_decorator_config_field_in(self):
        """Test the config_field decorator with 'in' constraint."""

        @configclass
        class J:
            value1: int = config_field(_in=[0, 1, 2], default=1)

        c = J()
        c.value1 = 1
        with self.assertRaises(ValueError):
            c.value1 = 3

    def test_config_class_decorator_config_field_constraints(self):
        """Test the config_field decorator with custom constraints."""

        @configclass
        class K:
            value1: int = config_field(
                constraints=[lambda x: x % 2 == 0], default=2
            )

        c = K()
        c.value1 = 2
        with self.assertRaises(ValueError):
            c.value1 = 1

    def test_config_class_decorator_config_field_gt_lt(self):
        """Test decorator with both greater and less constraints."""

        @configclass
        class L:
            value1: int = config_field(gt=0, lt=10, default=5)

        c = L()
        c.value1 = 5
        with self.assertRaises(ValueError):
            c.value1 = -1
        with self.assertRaises(ValueError):
            c.value1 = 11

    def test_type_attribute_is_added(self):
        """Test that the type attribute is added to the class."""

        @configclass
        class M:
            value1: int = config_field(gt=0, lt=10, default=5)

        self.assertEqual(M._config_class_type, "test_config.M")
        inspect.getmembers(M)
