"""
Unit Tests for HelloWorld Smart Contract

These tests use the `algorand-python-testing` library to test the contract
logic OFFLINE — no LocalNet or network connection required.
The library emulates AVM behavior in pure Python.

Reference: https://algorandfoundation.github.io/algorand-python-testing/
"""

from algopy import String, UInt64
from algopy_testing import algopy_testing_context

from smart_contracts.hello_world.contract import HelloWorld


def _box_key(name: str, counter: int) -> bytes:
    """Construct the expected box key: name_bytes + b"_" + itob(counter)."""
    return name.encode() + b"_" + counter.to_bytes(8, "big")


class TestHelloWorldUnit:
    """Unit tests for the HelloWorld contract using algopy_testing (offline)."""

    def test_hello_returns_greeting(self):
        """Test that hello() returns 'Hello, <name>'."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            result = contract.hello(String("John Doe"))

            assert result == String("Hello, John Doe")

    def test_hello_stores_greeting_in_box(self):
        """Test that hello() stores the greeting in a uniquely keyed box."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            contract.hello(String("John Doe"))

            expected_key = _box_key("John Doe", 0)
            assert ctx.ledger.box_exists(contract, expected_key)
            stored = ctx.ledger.get_box(contract, expected_key)
            assert b"Hello, John Doe" in stored

    def test_hello_stores_multiple_greetings(self):
        """Test that calling hello() multiple times creates separate boxes."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            contract.hello(String("Alice"))
            contract.hello(String("Bob"))
            contract.hello(String("Alice"))

            # Three separate boxes should exist
            key_0 = _box_key("Alice", 0)
            key_1 = _box_key("Bob", 1)
            key_2 = _box_key("Alice", 2)

            assert ctx.ledger.box_exists(contract, key_0)
            assert ctx.ledger.box_exists(contract, key_1)
            assert ctx.ledger.box_exists(contract, key_2)

            assert b"Hello, Alice" in ctx.ledger.get_box(contract, key_0)
            assert b"Hello, Bob" in ctx.ledger.get_box(contract, key_1)
            assert b"Hello, Alice" in ctx.ledger.get_box(contract, key_2)

    def test_counter_increments_on_each_call(self):
        """Test that the global counter increments correctly."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            assert contract.greeting_counter.value == UInt64(0)

            contract.hello(String("Alice"))
            assert contract.greeting_counter.value == UInt64(1)

            contract.hello(String("Bob"))
            assert contract.greeting_counter.value == UInt64(2)

            contract.hello(String("Alice"))
            assert contract.greeting_counter.value == UInt64(3)

    def test_hello_with_empty_name(self):
        """Test hello() with an empty string."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            result = contract.hello(String(""))

            assert result == String("Hello, ")
            expected_key = _box_key("", 0)
            assert ctx.ledger.box_exists(contract, expected_key)

    def test_hello_with_long_name(self):
        """Test hello() with a longer name."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            long_name = "Algorand Foundation Developer"
            result = contract.hello(String(long_name))

            assert result == String(f"Hello, {long_name}")
            expected_key = _box_key(long_name, 0)
            assert ctx.ledger.box_exists(contract, expected_key)
