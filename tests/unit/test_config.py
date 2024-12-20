"""Tests for config module."""
from unittest import TestCase

from config.config import ConfigClassRegistry, config_field, configclass


class TestConfig(TestCase):
    """Test Config class."""

    def test_config_class_registry_register(self):
        """Test registering a class in ConfigClassRegistry."""
        
        class A:
            pass
        ConfigClassRegistry.register(A)
        self.assertTrue(A in ConfigClassRegistry.list_classes())

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
        class A:
            pass
        class B:
            pass
        ConfigClassRegistry.register(A)
        ConfigClassRegistry.register(B)
        self.assertIn(A, ConfigClassRegistry.list_classes())
        self.assertIn(B, ConfigClassRegistry.list_classes())

    def test_config_class_registry_is_registered(self):
        """
        Test that the ConfigClassRegistry correctly registers.

        This test performs the following checks:
        1. Defines a class A and registers it with ConfigClassRegistry.
        2. Asserts that class A is registered in the ConfigClassRegistry.
        3. Defines a class B without registering it.
        4. Asserts that class B is not registered in the ConfigClassRegistry.
        """
        class A:
            pass
        ConfigClassRegistry.register(A)
        self.assertTrue(ConfigClassRegistry.is_registered(A))
        class B:
            pass
        self.assertFalse(ConfigClassRegistry.is_registered(B))

    def test_config_class_decorator(self):
        """Test the configclass decorator."""
        @configclass
        class C:
            value1: str
        self.assertTrue(C in ConfigClassRegistry.list_classes())

    def test_config_class_decorator_config_field(self):
        """Test the config_field decorator."""
        @configclass
        class C:
            value1: str = config_field()
        self.assertTrue(hasattr(C, "value1"))
        self.assertTrue(isinstance(C.value1, property))

    def test_config_class_decorator_config_field_gt(self):
        """Test the config_field decorator with greater than constraint."""
        @configclass
        class C:
            value1: int = config_field(gt=0, default=1)
        c = C()
        c.value1 = 1
        with self.assertRaises(ValueError):
            c.value1 = -1

    def test_config_class_decorator_config_field_lt(self):
        """Test the config_field decorator with less than constraint."""
        @configclass
        class C:
            value1: int = config_field(lt=0, default=-1)
        c = C()
        c.value1 = -1
        with self.assertRaises(ValueError):
            c.value1 = 1

    def test_config_class_decorator_config_field_in(self):
        """Test the config_field decorator with 'in' constraint."""
        @configclass
        class C:
            value1: int = config_field(_in=[0, 1, 2], default=1)
        c = C()
        c.value1 = 1
        with self.assertRaises(ValueError):
            c.value1 = 3

    def test_config_class_decorator_config_field_constraints(self):
        """Test the config_field decorator with custom constraints."""
        @configclass
        class C:
            value1: int = config_field(
                constraints=[lambda x: x % 2 == 0], 
                default=2)
        c = C()
        c.value1 = 2
        with self.assertRaises(ValueError):
            c.value1 = 1

    def test_config_class_decorator_config_field_gt_lt(self):
        """Test decorator with both greater and less constraints."""
        @configclass
        class C:
            value1: int = config_field(gt=0, lt=10, default=5)
        c = C()
        c.value1 = 5
        with self.assertRaises(ValueError):
            c.value1 = -1
        with self.assertRaises(ValueError):
            c.value1 = 11
