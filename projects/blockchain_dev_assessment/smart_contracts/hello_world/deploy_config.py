import base64
import logging

import algokit_utils

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


# define deployment behaviour based on supplied app spec
def deploy() -> None:
    from smart_contracts.artifacts.hello_world.hello_world_client import (
        HelloArgs,
        HelloWorldFactory,
    )

    algorand = algokit_utils.AlgorandClient.from_environment()
    deployer_ = algorand.account.from_environment("DEPLOYER")

    factory = algorand.client.get_typed_app_factory(
        HelloWorldFactory, default_sender=deployer_.address
    )

    app_client, result = factory.deploy(
        on_update=algokit_utils.OnUpdate.AppendApp,
        on_schema_break=algokit_utils.OnSchemaBreak.AppendApp,
    )

    algod = algorand.client.algod

    # Fund the app account to cover box storage MBR if balance is low
    app_balance = algod.account_info(app_client.app_address)["amount"]
    min_funding = 2_000_000  # 2 ALGO — supports ~100 greeting boxes
    if app_balance < min_funding:
        top_up = min_funding - app_balance
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(micro_algo=top_up),
                sender=deployer_.address,
                receiver=app_client.app_address,
            )
        )

    # --- Transaction 1: Call hello with "John Doe" ---
    name = "John Doe"
    counter = get_counter(algod, app_client.app_id)
    box_name = make_box_name(name, counter)
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=box_name)],
        ),
    )
    logger.info(
        f"Called hello on {app_client.app_name} ({app_client.app_id}) "
        f"with name={name}, received: {response.abi_return}"
    )

    # --- Transaction 2: Call hello again with a different name ---
    # Each call creates a NEW box instead of overwriting
    name = "Algorand Developer"
    counter = get_counter(algod, app_client.app_id)
    box_name = make_box_name(name, counter)
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=box_name)],
        ),
    )
    logger.info(
        f"Called hello on {app_client.app_name} ({app_client.app_id}) "
        f"with name={name}, received: {response.abi_return}"
    )
