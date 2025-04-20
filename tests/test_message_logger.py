import pytest
import syrupy

from aiokem.message_logger import redact_fields
from tests.conftest import load_fixture_file


@pytest.mark.parametrize(
    "message_file",
    [
        "homes.json",
        "generator_data.json",
    ],
)
async def test_message_logger(
    message_file: str, snapshot: syrupy.SnapshotAssertion
) -> None:
    resp = load_fixture_file(message_file)
    result = redact_fields(resp)
    assert result == snapshot
