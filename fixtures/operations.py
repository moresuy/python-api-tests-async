import pytest
import pytest_asyncio

from clients.operations_client import OperationsClient, get_operations_client
from config import Settings
from schema.operations import OperationSchema


@pytest.fixture
def operations_client(settings: Settings) -> OperationsClient:
    return get_operations_client(settings)


@pytest_asyncio.fixture
async def function_operation(operations_client: OperationsClient) -> OperationSchema:
    operation = await operations_client.create_operation()
    yield operation

    await operations_client.delete_operation_api(operation.id)
