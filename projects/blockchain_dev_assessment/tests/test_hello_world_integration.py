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

    # Fund the app for box storage MBR
    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer.address,
                receiver=app_client.app_address,
            )
        )

    return app_client


class TestHelloWorldIntegration:
    """Integration tests — deployed on LocalNet."""

    def test_hello_returns_correct_greeting(self, app_client):
        """Test that hello() returns the expected greeting on-chain."""
        response = app_client.send.hello(
            args=HelloArgs(name="John Doe"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=b"greeting")
                ],
            ),
        )

        assert response.abi_return == "Hello, John Doe"

    def test_box_storage_contains_greeting(self, app_client, algorand):
        """Test that box storage contains the greeting after calling hello()."""
        # Call hello to populate the box
        app_client.send.hello(
            args=HelloArgs(name="Algorand Developer"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=b"greeting")
                ],
            ),
        )

        # Read box directly from the chain
        algod = algorand.client.algod
        box_response = algod.application_box_by_name(
            app_client.app_id, b"greeting"
        )
        box_value = base64.b64decode(box_response["value"]).decode()

        assert box_value == "Hello, Algorand Developer"

    def test_box_is_overwritten_on_second_call(self, app_client, algorand):
        """Test that a second call overwrites the box value."""
        # First call
        app_client.send.hello(
            args=HelloArgs(name="Alice"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=b"greeting")
                ],
            ),
        )

        # Second call — should overwrite
        app_client.send.hello(
            args=HelloArgs(name="Bob"),
            params=algokit_utils.CommonAppCallParams(
                box_references=[
                    algokit_utils.BoxReference(app_id=0, name=b"greeting")
                ],
            ),
        )

        # Verify final box value
        algod = algorand.client.algod
        box_response = algod.application_box_by_name(
            app_client.app_id, b"greeting"
        )
        box_value = base64.b64decode(box_response["value"]).decode()

        assert box_value == "Hello, Bob"
        assert "Alice" not in box_value

    def test_app_has_box_listed(self, app_client, algorand):
        """Test that the app's box list includes the 'greeting' box."""
        algod = algorand.client.algod
        boxes = algod.application_boxes(app_client.app_id)

        box_names = [
            base64.b64decode(b["name"]).decode() for b in boxes["boxes"]
        ]
        assert "greeting" in box_names
