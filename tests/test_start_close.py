import unittest

from minject.inject import close_method, start_method
from minject.registry import initialize


class TestStartStopDecorators(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = initialize()
        self.start_called = False
        self.close_called = False

    def test_start_method(self) -> None:
        """Test that start_method decorator correctly sets up a start function."""

        class TestClass:
            def __init__(self) -> None:
                self.value = 0

            def increment(self) -> None:
                self.value += 1

        def start_func(obj: TestClass) -> None:
            self.start_called = True
            obj.increment()

        # Apply the start_method decorator
        start_method(TestClass, start_func)

        # Create an instance through the registry
        instance = self.registry[TestClass]

        # Verify the start function was called
        self.assertTrue(self.start_called)
        self.assertEqual(instance.value, 1)

    def test_close_method(self) -> None:
        """Test that close_method decorator correctly sets up a close function."""

        class TestClass:
            def __init__(self) -> None:
                self.value = 0

            def increment(self) -> None:
                self.value += 1

        def close_func(obj: TestClass) -> None:
            self.close_called = True
            obj.increment()

        self.assertFalse(self.close_called)

        # Apply the close_method decorator
        close_method(TestClass, close_func)

        # Create an instance through the registry
        instance = self.registry[TestClass]

        # Close the registry
        self.registry.close()

        # Verify the close function was called
        self.assertTrue(self.close_called)
        self.assertEqual(instance.value, 1)

    def test_start_and_close_methods(self) -> None:
        """Test that both start and close methods work together."""

        class TestClass:
            def __init__(self) -> None:
                self.value = 0

            def increment(self) -> None:
                self.value += 1

        def start_func(obj: TestClass) -> None:
            self.start_called = True
            obj.increment()

        def close_func(obj: TestClass) -> None:
            self.close_called = True
            obj.increment()

        # Apply both decorators
        start_method(TestClass, start_func)
        close_method(TestClass, close_func)

        # Create an instance through the registry
        instance = self.registry[TestClass]

        # Verify the start function was called
        self.assertTrue(self.start_called)
        self.assertEqual(instance.value, 1)
        self.assertFalse(self.close_called)

        # Close the registry
        self.registry.close()

        # Verify the close function was called
        self.assertTrue(self.close_called)
        self.assertEqual(instance.value, 2)
