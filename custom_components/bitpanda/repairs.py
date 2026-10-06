"""The dialog of the upgrade's repair issue for the entities it could not
migrate (migration.ISSUE_NOT_MIGRATED), the only issue with a dialog.

The dialog lists the entities as they are when it opens -- deleted by hand
or renamed since the last start, they are shown as they are now; with none
left, it closes the issue at once. Confirmed, it deletes them and each old
device they leave empty (migration.async_delete_left_over), and Home
Assistant deletes the issue. Closed, it deletes nothing, and the issue
stays.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

import voluptuous as vol
from homeassistant.components.repairs import ConfirmRepairFlow, RepairsFlow
from homeassistant.core import HomeAssistant

from .migration import (
    ISSUE_NOT_MIGRATED,
    async_delete_left_over,
    entity_id_list,
    left_over_entity_ids,
)

if TYPE_CHECKING:
    # Not in Home Assistant 2025.5, which typed the results as FlowResult.
    from homeassistant.components.repairs import RepairsFlowResult


class LeftOverEntitiesFlow(RepairsFlow):
    """Delete the entities the upgrade left alone, once the user confirms."""

    def __init__(self) -> None:
        self._entity_ids: list[str] = []

    @property
    def _entry_id(self) -> str:
        """The Portfolio's entry, from the issue's data, which every raise
        of the issue sets (migration.async_raise_not_migrated_issue)."""
        return cast(dict[str, str], self.data)["entry_id"]

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """Open the dialog on what is left now; with nothing left, close the
        issue."""
        self._entity_ids = left_over_entity_ids(self.hass, self._entry_id)
        if not self._entity_ids:
            return self.async_create_entry(data={})
        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> RepairsFlowResult:
        """List the entities; delete them once confirmed."""
        if user_input is not None:
            async_delete_left_over(self.hass, self._entry_id, self._entity_ids)
            return self.async_create_entry(data={})
        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema({}),
            description_placeholders={"entities": entity_id_list(self._entity_ids)},
        )


async def async_create_fix_flow(
    hass: HomeAssistant, issue_id: str, data: dict[str, str | int | float | None] | None
) -> RepairsFlow:
    """The dialog of the issue that has one (see above). Another issue, were
    one ever fixable without a dialog of its own, gets Home Assistant's plain
    confirmation -- never the dialog that deletes."""
    if issue_id == ISSUE_NOT_MIGRATED:
        return LeftOverEntitiesFlow()
    return ConfirmRepairFlow()
