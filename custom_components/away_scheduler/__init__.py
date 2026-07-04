"""
Custom integration to integrate integration_blueprint with Home Assistant.

For more details about this integration, please refer to
https://github.com/ludeeus/integration_blueprint
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import Platform
from homeassistant.loader import async_get_loaded_integration
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN, LOGGER, MASTER_SUBENTRY_TYPE
from .coordinator import SchedulerDatUpdateCoordinator
from .data import IntegrationBlueprintData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from .data import IntegrationBlueprintConfigEntry

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
]

MASTER_SUBENTRY_TITLE = "master"


def _get_master_subentry(
    entry: IntegrationBlueprintConfigEntry,
) -> ConfigSubentry | None:
    """Return the master subentry if it already exists."""
    return next(
        (
            subentry
            for subentry in entry.subentries.values()
            if subentry.subentry_type == MASTER_SUBENTRY_TYPE
        ),
        None,
    )


def _ensure_master_subentry(
    hass: HomeAssistant, entry: IntegrationBlueprintConfigEntry
) -> None:
    """Create the master subentry once for this config entry."""
    if _get_master_subentry(entry) is not None:
        return

    hass.config_entries.async_add_subentry(
        entry,
        ConfigSubentry(
            data={},
            subentry_type=MASTER_SUBENTRY_TYPE,
            title=MASTER_SUBENTRY_TITLE,
            unique_id=MASTER_SUBENTRY_TYPE,
            ),
        )


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Set up this integration using UI."""
    _ensure_master_subentry(hass, entry)

    master_subentry = _get_master_subentry(entry)

    coordinator = SchedulerDatUpdateCoordinator(
        hass=hass,
        logger=LOGGER,
        name=DOMAIN,
        update_interval=timedelta(hours=1),
    )
    coordinator.config_entry = entry

    integration = async_get_loaded_integration(hass, DOMAIN)
    entry.runtime_data = IntegrationBlueprintData(
        coordinator=coordinator,
        integration=integration,
        scheduler_enabled=master_subentry.data.get(
            "scheduler_enabled",
            entry.options.get("scheduler_enabled", True),
        )
        if master_subentry is not None
        else entry.options.get("scheduler_enabled", True),
    )

    # https://developers.home-assistant.io/docs/integration_fetching_data#coordinated-single-api-poll-for-data-for-all-entities
    await coordinator.async_config_entry_first_refresh()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_setup_subentry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
    subentry: ConfigSubentry,
) -> bool:
    """Set up a subentry and register its devices."""

    if subentry.subentry_type == "scheduler_group":
        group_name = subentry.data.get("name", subentry.title)
        devices = subentry.data.get("devices", [])

        dev_reg = dr.async_get(hass)

        for entity_id in devices:
            friendly_name = entity_id.split(".")[-1].replace("_", " ").title()

            dev_reg.async_get_or_create(
                config_entry_id=entry.entry_id,
                config_subentry_id=subentry.subentry_id,
                identifiers={(DOMAIN, f"{subentry.subentry_id}_{entity_id}")},
                name=f"{group_name} - {friendly_name}",
                manufacturer="Master Scheduler",
                model="Scheduled Member",
            )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> bool:
    """Handle removal of an entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant,
    entry: IntegrationBlueprintConfigEntry,
) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)