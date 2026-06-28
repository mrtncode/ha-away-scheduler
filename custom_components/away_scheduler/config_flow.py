"""Adds config flow for Blueprint."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigSubentryFlow, ConfigFlowResult, SubentryFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TimeSelector

from .const import DOMAIN, LOGGER


class MasterSchedulerFlowHandler(config_entries.ConfigFlow, domain="away_scheduler"):
    """Handle the global master config flow."""

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        """Create the singular master hub instance."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Device Scheduler Master", data={})

        return self.async_show_form(step_id="user")

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {"device_schedule": DeviceScheduleSubentryFlowHandler}


class DeviceScheduleSubentryFlowHandler(config_entries.ConfigSubentryFlow):
    """Handle adding/editing schedules for specific devices."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Add a specific device scheduling target."""
        errors = {}
        # Fetch parent config entry context natively using the 2025 helper method
        parent_entry = self._get_entry()

        if user_input is not None:
            target_device = user_input["device_entity"]

            # Manually check for subentry collisions
            for subentry in parent_entry.subentries.values():
                if subentry.data.get("device_entity") == target_device:
                    errors["base"] = "already_configured"
                    break

            if not errors:
                # Subentry creation uses async_create_entry natively
                # Providing subentry_type allows Home Assistant to distinguish child data profiles
                return self.async_create_entry(
                    title=f"Schedule for {target_device}",
                    data={
                        **user_input,
                        "subentry_type": "device_schedule"
                    }
                )

        schema = vol.Schema({
            vol.Required("device_entity"): EntitySelector(EntitySelectorConfig()),
            vol.Required("start_time"): TimeSelector(),
            vol.Required("end_time"): TimeSelector(),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
