"""
Standalone script to call the HelloWorld contract's hello method.

Usage:
    poetry run python call_hello.py                          # LocalNet, default name
    poetry run python call_hello.py "Alice"                  # LocalNet, custom name
    poetry run python call_hello.py --network testnet        # Testnet, default name
    poetry run python call_hello.py --network testnet "Bob"  # Testnet, custom name

Each run creates a new on-chain app call transaction and updates the
"greeting" box storage with "Hello, <name>".
"""

import argparse
import logging
import os
from pathlib import Path

import algokit_utils
from dotenv import load_dotenv

from smart_contracts.artifacts.hello_world.hello_world_client import (
    HelloArgs,
    HelloWorldFactory,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-10s: %(message)s")
logger = logging.getLogger(__name__)


def call_hello(name: str, network: str) -> None:
    # Clear network-related env vars so stale values from a previous
    # "source .env.testnet" don't leak into a localnet run (or vice-versa).
    for key in ("ALGOD_SERVER", "ALGOD_PORT", "ALGOD_TOKEN",
                "INDEXER_SERVER", "INDEXER_PORT", "INDEXER_TOKEN",
                "DEPLOYER_MNEMONIC"):
        os.environ.pop(key, None)

    # Load the env file for the chosen network
    env_file = Path(__file__).parent / f".env.{network}"
    if env_file.exists():
        load_dotenv(env_file, override=True)
        logger.info(f"Loaded environment from {env_file.name}")
    else:
        load_dotenv(override=True)
        logger.info(f"No .env.{network} found, using default .env")

    logger.info(f"Target network: {network}")

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
    parser = argparse.ArgumentParser(description="Call the HelloWorld contract")
    parser.add_argument("name", nargs="?", default="John Doe", help="Name to greet (default: John Doe)")
    parser.add_argument("--network", choices=["localnet", "testnet"], default="localnet",
                        help="Target network (default: localnet)")
    args = parser.parse_args()

    call_hello(args.name, args.network)
