"""
Integration Tests for HelloWorld Smart Contract

These tests deploy and call the contract on Algorand LocalNet,
verifying real on-chain behavior including box storage.

Requires: LocalNet running (`algokit localnet start`)

Reference: https://dev.algorand.co/concepts/smart-contracts/testing/local
"""

import base64
import logging

import algokit_utils
import pytest
from dotenv import load_dotenv

from smart_contracts.artifacts.hello_world.hello_world_client import (
    HelloArgs,
    HelloWorldFactory,
)

load_dotenv()
logger = logging.getLogger(__name__)


def get_counter(algod, app_id: int) -> int:
    """Read the greeting counter from the app's global state."""
    app_info = algod.application_info(app_id)
    for kv in app_info.get("params", {}).get("global-state", []):
        key = base64.b64decode(kv["key"]).decode()
        if key == "counter":
            return kv["value"]["uint"]
    return 0


def make_box_name(name: str, counter: int) -> bytes:
    """Construct the box name matching the contract's key format."""
    return name.encode() + b"_" + counter.to_bytes(8, "big")


@pytest.fixture(scope="module")
def algorand() -> algokit_utils.AlgorandClient:
    """Create an AlgorandClient connected to LocalNet."""
    return algokit_utils.AlgorandClient.from_environment()


@pytest.fixture(scope="module")
def deployer(algorand: algokit_utils.AlgorandClient) -> algokit_utils.SigningAccount:
    """Get the deployer account from environment."""
    return algorand.account.from_environment("DEPLOYER")


@pytest.fixture(scope="module")
def app_client(
    algorand: algokit_utils.AlgorandClient,
    deployer: algokit_utils.SigningAccount,
):
    """Deploy the HelloWorld contract and return the typed client."""
    factory = algorand.client.get_typed_app_factory(
        HelloWorldFactory, default_sender=deployer.address
    )

    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    # Fund the app for box storage MBR if balance is low
    algod = algorand.client.algod
    app_balance = algod.account_info(app_client.app_address)["amount"]
    min_funding = 2_000_000  # 2 ALGO — supports ~100 greeting boxes
    if app_balance < min_funding:
        top_up = min_funding - app_balance
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(micro_algo=top_up),
                sender=deployer.address,
                receiver=app_client.app_address,
            )
        )

    return app_client


class TestHelloWorldIntegration:
    """Integration tests — deployed on LocalNet."""

    def test_hello_returns_correct_greeting(self, app_client, algorand):
        """Test that hello() returns the expected greeting on-chain."""
        algod = algorand.client.algod
        counter = get_counter(algod, app_client.app_id)
        box_name = make_box_name("John Doe", counter)

        response = app_client.send.hello(
            args=HelloArgs(name="John Doe"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=box_name)
                ],
            ),
        )

        assert response.abi_return == "Hello, John Doe"

    def test_box_storage_contains_greeting(self, app_client, algorand):
        """Test that box storage contains the greeting after calling hello()."""
        algod = algorand.client.algod
        counter = get_counter(algod, app_client.app_id)
        box_name = make_box_name("Algorand Developer", counter)

        app_client.send.hello(
            args=HelloArgs(name="Algorand Developer"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=box_name)
                ],
            ),
        )

        # Read box directly from the chain
        box_response = algod.application_box_by_name(app_client.app_id, box_name)
        box_value = base64.b64decode(box_response["value"]).decode()

        assert box_value == "Hello, Algorand Developer"

    def test_multiple_greetings_stored_separately(self, app_client, algorand):
        """Test that multiple calls create separate boxes on-chain."""
        algod = algorand.client.algod

        # Call 1: Alice
        counter_1 = get_counter(algod, app_client.app_id)
        box_1 = make_box_name("Alice", counter_1)
        app_client.send.hello(
            args=HelloArgs(name="Alice"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=box_1)
                ],
            ),
        )

        # Call 2: Alice again — should get a different box
        counter_2 = get_counter(algod, app_client.app_id)
        box_2 = make_box_name("Alice", counter_2)
        app_client.send.hello(
            args=HelloArgs(name="Alice"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=box_2)
                ],
            ),
        )

        assert counter_2 == counter_1 + 1
        assert box_1 != box_2

        # Both boxes should exist with correct values
        val_1 = base64.b64decode(
            algod.application_box_by_name(app_client.app_id, box_1)["value"]
        ).decode()
        val_2 = base64.b64decode(
            algod.application_box_by_name(app_client.app_id, box_2)["value"]
        ).decode()

        assert val_1 == "Hello, Alice"
        assert val_2 == "Hello, Alice"

    def test_app_has_multiple_boxes(self, app_client, algorand):
        """Test that the app's box list includes multiple greeting boxes."""
        algod = algorand.client.algod
        boxes = algod.application_boxes(app_client.app_id)

        # Previous tests created at least 4 boxes
        assert len(boxes["boxes"]) >= 4
