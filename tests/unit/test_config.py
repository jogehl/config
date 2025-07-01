"""Tests for config module."""

import dis
import importlib.util
import inspect
import os
from collections.abc import Callable
from typing import Literal
from unittest import TestCase
from pydantic import ValidationError, field_validator
from pydantic_core import to_json

from simple_config_builder import ConfigClassRegistry, Configclass, Field


class TestConfig(TestCase):
    """Test Config class."""

    def test_config_class_registry_register(self):
        """Test registering a class in ConfigClassRegistry."""

        class A(Configclass):
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

        class F(Configclass):
            value1: str

        self.assertTrue(
            ConfigClassRegistry.get_class_str_from_class(F)
            in ConfigClassRegistry.list_classes()
        )

    def test_config_class_decorator_config_field(self):
        """Test the config_field decorator."""

        class G(Configclass):
            value1: str

        print(G.__dict__)
        self.assertTrue("value1" in G.model_fields)

    def test_config_class_decorator_config_field_gt(self):
        """Test the config_field decorator with greater than constraint."""

        class H(Configclass):
            value1: int = Field(gt=0, default=1)

        c = H()
        c.value1 = 1
        with self.assertRaises(ValidationError):
            c.value1 = -1

    def test_config_class_decorator_config_field_lt(self):
        """Test the config_field decorator with less than constraint."""

        class Il(Configclass):
            value1: int = Field(lt=0, default=-1)

        c = Il()
        c.value1 = -1
        with self.assertRaises(ValidationError):
            c.value1 = 1

    def test_config_class_decorator_config_field_in(self):
        """Test the config_field decorator with 'in' constraint."""

        class J(Configclass):
            value1: Literal[1, 2] = Field(default=1)

        c = J()
        c.value1 = 1
        with self.assertRaises(ValueError):
            c.value1 = 3

    def test_config_class_decorator_config_field_constraints(self):
        """Test the config_field decorator with custom constraints."""

        class K(Configclass):
            value1: int

            @field_validator("value1")
            def check_value1(cls, v):
                # check if value % 2 is 0
                if v % 2 != 0:
                    raise ValueError("value1 must be an even number")
                return v

        c = K(value1=0)
        c.value1 = 2
        with self.assertRaises(ValueError):
            c.value1 = 1

    def test_config_class_decorator_config_field_gt_lt(self):
        """Test decorator with both greater and less constraints."""

        class L(Configclass):
            value1: int = Field(gt=0, lt=10, default=5)

        c = L()
        c.value1 = 5
        with self.assertRaises(ValidationError):
            c.value1 = -1
        with self.assertRaises(ValidationError):
            c.value1 = 11

    def test_type_attribute_is_added(self):
        """Test that the type attribute is added to the class."""

        class M(Configclass):
            value1: int = Field(gt=0, lt=10, default=5)

        self.assertEqual(
            "_config_class_type" in M.__private_attributes__, True
        )
        inspect.getmembers(M)

    def test_callable_type(self):
        """Test that the type attribute is added to the class."""

        class N(Configclass):
            func1: Callable

        n = N(func1=fun)
        self.assertEqual(n.func1.__code__, fun.__code__)

        json = n.model_dump_json()
        n = N.model_validate_json(json)
        self.assertEqual(fun.__code__, n.func1.__code__)

    def test_list_of_callables(self):
        """Test that a list of callables is handled correctly."""

        class Op(Configclass):
            funcs: list[Callable]

        n = Op(funcs=[fun, fun])
        self.assertEqual(len(n.funcs), 2)
        self.assertEqual(n.funcs[0].__code__, fun.__code__)
        self.assertEqual(n.funcs[1].__code__, fun.__code__)

        json = n.model_dump_json()
        n = Op.model_validate_json(json)
        self.assertEqual(len(n.funcs), 2)
        self.assertEqual(n.funcs[0].__code__, fun.__code__)
        self.assertEqual(n.funcs[1].__code__, fun.__code__)

    def test_dict_of_callables(self):
        """Test that a dictionary of callables is handled correctly."""

        class P(Configclass):
            funcs: dict[str, Callable]

        n = P(funcs={"func1": fun, "func2": fun})
        self.assertEqual(len(n.funcs), 2)
        self.assertEqual(n.funcs["func1"].__code__, fun.__code__)
        self.assertEqual(n.funcs["func2"].__code__, fun.__code__)

        json = n.model_dump_json()
        n = P.model_validate_json(json)
        self.assertEqual(len(n.funcs), 2)
        self.assertEqual(n.funcs["func1"].__code__, fun.__code__)
        self.assertEqual(n.funcs["func2"].__code__, fun.__code__)

    def test_callable_type_from_other_file(self):
        """Test that the type attribute is added to the class."""
        from os.path import dirname

        # import function from external module for testing
        current_file_location = __file__
        current_file_path = dirname(current_file_location)
        pacakge_file_path = dirname(dirname(current_file_path))
        external_file_location = os.path.join(
            pacakge_file_path, "external_func_for_testing.py"
        )
        # make path to external file
        spec = importlib.util.spec_from_file_location(
            "external_func_for_testing", external_file_location
        )
        if spec is None:
            raise ValueError("Spec is None")
        external_func = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            raise ValueError("Loader is None")
        spec.loader.exec_module(external_func)
        func = getattr(external_func, "fun")

        class OClass(Configclass):
            func1: Callable
            number: int = Field(default=1)

        n = OClass(func1=func)
        self.assertEqual(dis.dis(func), dis.dis(n.func1))

        json = to_json(n)
        n = OClass.model_validate_json(json)
        self.assertEqual(func.__code__, n.func1.__code__)

    def test_literal(self):
        """Test if Literal works as expected."""

        class P(Configclass):
            value1: Literal["a", "b"]

        c = P(value1="a")
        json = c.model_dump_json()
        c = P.model_validate_json(json)
        self.assertEqual(c.value1, "a")


def fun():
    """Test function."""
    return True
