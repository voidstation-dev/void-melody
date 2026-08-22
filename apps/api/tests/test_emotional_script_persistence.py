import pytest

from app.services.script_parser import parse_script
from app.services.script_store import (
    ScriptRevisionConflict,
    create_script,
    update_script,
)


@pytest.mark.asyncio
async def test_script_revision_is_pinned_and_conflicts_are_explicit(async_session):
    document = parse_script("Người dẫn: Một câu chuyện.", format="dialogue_txt")
    created = await create_script(async_session, document, title="Đêm mưa")

    assert created.revision == 1
    assert created.schema_version == 1
    assert created.title == "Đêm mưa"

    document.title = "Đêm mưa — bản sửa"
    updated = await update_script(
        async_session,
        created.id,
        document,
        expected_revision=1,
    )
    assert updated.revision == 2

    with pytest.raises(ScriptRevisionConflict):
        await update_script(
            async_session,
            created.id,
            document,
            expected_revision=1,
        )

