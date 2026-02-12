"""
Standalone script to call the HelloWorld contract's hello method.

Usage:
    poetry run python call_hello.py                          # LocalNet, default name
    poetry run python call_hello.py "Alice"                  # LocalNet, custom name
    poetry run python call_hello.py --network testnet        # Testnet, default name
    poetry run python call_hello.py --network testnet "Bob"  # Testnet, custom name

Each run creates a new on-chain app call transaction and stores
"Hello, <name>" in a NEW box (every greeting is preserved).
"""

import argparse
import base64
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

    # Read current counter to construct the box name
    algod = algorand.client.algod
    counter = get_counter(algod, app_client.app_id)
    box_name = make_box_name(name, counter)

    logger.info(f"Creating greeting #{counter} for '{name}'")

    # Call the hello method — creates a NEW box for this greeting
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=box_name)],
        ),
    )

    logger.info(f"Transaction successful!")
    logger.info(f"  Name passed:     {name}")
    logger.info(f"  Return value:    {response.abi_return}")
    logger.info(f"  App ID:          {app_client.app_id}")
    logger.info(f"  Greeting #{counter} stored in box storage")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Call the HelloWorld contract")
    parser.add_argument("name", nargs="?", default="John Doe", help="Name to greet (default: John Doe)")
    parser.add_argument("--network", choices=["localnet", "testnet"], default="localnet",
                        help="Target network (default: localnet)")
    args = parser.parse_args()

    call_hello(args.name, args.network)
