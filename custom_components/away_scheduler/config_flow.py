"""Adds config flow for Blueprint."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigSubentryFlow, ConfigFlowResult, SubentryFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    TextSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    DurationSelector,
)

from .const import DOMAIN


class MasterSchedulerFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the global master config flow."""

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Create the singular master hub instance and select Sun entity."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(
                title="Device Scheduler Master",
                data={"sun_entity": user_input["sun_entity"]}
            )

        schema = vol.Schema({
            vol.Required("sun_entity", default="sun.sun"): EntitySelector(
                EntitySelectorConfig(domain="sun")
            ),
        })

        return self.async_show_form(step_id="user", data_schema=schema)

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            "scheduler_group": GroupSubentryFlowHandler,
        }


class GroupSubentryFlowHandler(config_entries.ConfigSubentryFlow):
    """Handle adding/editing scheduling groups with dynamic per-device naming."""

    def __init__(self) -> None:
        """Initialize the subentry flow."""
        self._init_data: dict[str, Any] = {}

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguration of an existing group."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Step 1: Manage the group name and selected devices."""
        errors = {}
        parent_entry = self._get_entry()
        subentry_id = getattr(self, "subentry_id", None) or self.context.get("subentry_id")

        current_data = parent_entry.subentries[subentry_id].data if subentry_id and subentry_id in parent_entry.subentries else {}

        if user_input is not None:
            group_name = user_input["name"]

            for sid, subentry in parent_entry.subentries.items():
                if subentry.data.get("subentry_type") == "scheduler_group" and subentry.data.get("name") == group_name and sid != subentry_id:
                    errors["base"] = "group_already_exists"
                    break

            if not errors:
                self._init_data.update(user_input)
                return await self.async_step_device_names()

        schema = vol.Schema({
            vol.Required("name", default=current_data.get("name")): TextSelector(),
            vol.Required("devices", default=current_data.get("devices", [])): EntitySelector(
                EntitySelectorConfig(multiple=True)
            ),
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_device_names(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Step 2: Dynamically request a custom name for every selected device."""
        parent_entry = self._get_entry()
        subentry_id = getattr(self, "subentry_id", None) or self.context.get("subentry_id")
        current_data = parent_entry.subentries[subentry_id].data if subentry_id and subentry_id in parent_entry.subentries else {}

        existing_custom_names = current_data.get("custom_names", {})

        selected_devices = self._init_data.get("devices", [])

        if user_input is not None:
            self._init_data["custom_names"] = user_input
            return await self.async_step_config()

        fields = {}
        for entity_id in selected_devices:
            friendly_default = entity_id.split(".")[-1].replace("_", " ").title()
            current_custom_name = existing_custom_names.get(entity_id, friendly_default)

            fields[vol.Optional(entity_id, default=current_custom_name)] = TextSelector()

        return self.async_show_form(
            step_id="device_names",
            data_schema=vol.Schema(fields)
        )

    async def async_step_config(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Step 3: Fine-tune the scheduling behaviors."""
        parent_entry = self._get_entry()
        subentry_id = getattr(self, "subentry_id", None) or self.context.get("subentry_id")
        current_data = parent_entry.subentries[subentry_id].data if subentry_id and subentry_id in parent_entry.subentries else {}

        if user_input is not None:
            final_data = {
                **self._init_data,
                **user_input,
                "subentry_type": "scheduler_group"
            }

            if "device_states" in current_data:
                final_data["device_states"] = current_data["device_states"]

            return self.async_create_entry(
                title=f"Group: {final_data['name']}",
                data=final_data
            )

        default_offset = current_data.get("sunset_offset_range", {"minutes": 0})

        schema = vol.Schema({
            vol.Required("sunset_offset_range", default=default_offset): DurationSelector(),
            vol.Required("duration", default=current_data.get("duration", "mid")): SelectSelector(
                SelectSelectorConfig(options=["short", "mid", "long", "custom"], mode=SelectSelectorMode.DROPDOWN)
            ),
            vol.Required("randomness_level", default=current_data.get("randomness_level", "mid")): SelectSelector(
                SelectSelectorConfig(options=["low", "mid", "high"], mode=SelectSelectorMode.LIST)
            ),
            vol.Required("activity_level", default=current_data.get("activity_level", "mid")): SelectSelector(
                SelectSelectorConfig(options=["low", "mid", "high"], mode=SelectSelectorMode.LIST)
            ),
        })

        return self.async_show_form(step_id="config", data_schema=schema)