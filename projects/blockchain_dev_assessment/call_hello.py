"""
Standalone script to call the HelloWorld contract's hello method.

Usage:
    poetry run python call_hello.py                  # uses default name "John Doe"
    poetry run python call_hello.py "Your Name"      # pass any name as argument

Each run creates a new on-chain app call transaction and updates the
"greeting" box storage with "Hello, <name>".
"""

import sys
import logging

import algokit_utils
from dotenv import load_dotenv

from smart_contracts.artifacts.hello_world.hello_world_client import (
    HelloArgs,
    HelloWorldFactory,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-10s: %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()


def call_hello(name: str) -> None:
    # Connect to the Algorand network (LocalNet by default via .env)
    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer = algorand.account.from_environment("DEPLOYER")

    # Get the typed app factory and find the existing deployed contract
    factory = algorand.client.get_typed_app_factory(
        HelloWorldFactory, default_sender=deployer.address
    )
    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    logger.info(f"Using HelloWorld app ID: {app_client.app_id}")

    # Call the hello method — this creates a new on-chain transaction
    # and stores "Hello, <name>" in box storage
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=b"greeting")],
        ),
    )

    logger.info(f"Transaction successful!")
    logger.info(f"  Name passed:     {name}")
    logger.info(f"  Return value:    {response.abi_return}")
    logger.info(f"  App ID:          {app_client.app_id}")
    logger.info(f"  Box 'greeting' now contains: {response.abi_return}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "John Doe"
    call_hello(name)
