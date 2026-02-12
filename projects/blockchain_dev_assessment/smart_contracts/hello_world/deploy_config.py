import logging

import algokit_utils

logger = logging.getLogger(__name__)


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

    # Fund the app account to cover box storage MBR (Minimum Balance Requirement)
    if result.operation_performed in [
        algokit_utils.OperationPerformed.Create,
        algokit_utils.OperationPerformed.Replace,
    ]:
        algorand.send.payment(
            algokit_utils.PaymentParams(
                amount=algokit_utils.AlgoAmount(algo=1),
                sender=deployer_.address,
                receiver=app_client.app_address,
            )
        )

    # --- Transaction 1: Call hello with "John Doe" ---
    name = "John Doe"
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=b"greeting")],
        ),
    )
    logger.info(
        f"Called hello on {app_client.app_name} ({app_client.app_id}) "
        f"with name={name}, received: {response.abi_return}"
    )

    # --- Transaction 2: Call hello again with a different name ---
    # This overwrites the box value, demonstrating that box storage is mutable
    name = "Algorand Developer"
    response = app_client.send.hello(
        args=HelloArgs(name=name),
        params=algokit_utils.CommonAppCallParams(
            box_references=[algokit_utils.BoxReference(app_id=0, name=b"greeting")],
        ),
    )
    logger.info(
        f"Called hello on {app_client.app_name} ({app_client.app_id}) "
        f"with name={name}, received: {response.abi_return}"
    )
