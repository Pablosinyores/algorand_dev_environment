"""
Unit Tests for HelloWorld Smart Contract

These tests use the `algorand-python-testing` library to test the contract
logic OFFLINE — no LocalNet or network connection required.
The library emulates AVM behavior in pure Python.

Reference: https://algorandfoundation.github.io/algorand-python-testing/
"""

import pytest
from algopy import String
from algopy_testing import algopy_testing_context

from smart_contracts.hello_world.contract import HelloWorld


class TestHelloWorldUnit:
    """Unit tests for the HelloWorld contract using algopy_testing (offline)."""

    def test_hello_returns_greeting(self):
        """Test that hello() returns 'Hello, <name>'."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            result = contract.hello(String("John Doe"))

            assert result == String("Hello, John Doe")

    def test_hello_stores_greeting_in_box(self):
        """Test that hello() stores the greeting in box storage."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            contract.hello(String("John Doe"))

            # Verify box exists and contains the correct value
            assert ctx.ledger.box_exists(contract, b"greeting")
            stored = ctx.ledger.get_box(contract, b"greeting")
            assert b"Hello, John Doe" in stored

    def test_hello_overwrites_box_on_second_call(self):
        """Test that calling hello() again overwrites the box value."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            contract.hello(String("John Doe"))
            contract.hello(String("Alice"))

            stored = ctx.ledger.get_box(contract, b"greeting")
            assert b"Alice" in stored
            assert b"John Doe" not in stored

    def test_hello_with_empty_name(self):
        """Test hello() with an empty string."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            result = contract.hello(String(""))

            assert result == String("Hello, ")

    def test_hello_with_long_name(self):
        """Test hello() with a longer name."""
        with algopy_testing_context() as ctx:
            contract = HelloWorld()

            long_name = "Algorand Foundation Developer"
            result = contract.hello(String(long_name))

            assert result == String(f"Hello, {long_name}")
            assert ctx.ledger.box_exists(contract, b"greeting")
