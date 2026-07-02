"""Switch platform for away_scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo

from .const import MASTER_SUBENTRY_TYPE
from .entity import SchedulerBaseEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SchedulerDatUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="away_scheduler",
        name="Away Scheduler",
        icon="mdi:format-quote-close",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""
    master_subentry = next(
        (
            subentry
            for subentry in entry.subentries.values()
            if subentry.subentry_type == MASTER_SUBENTRY_TYPE
        ),
        None,
    )

    if master_subentry is None:
        return

    async_add_entities(
        [
            SchedulerSwitch(
                coordinator=entry.runtime_data.coordinator,
                entity_description=ENTITY_DESCRIPTIONS[0],
                subentry=master_subentry,
            )
        ],
        config_subentry_id=master_subentry.subentry_id,
    )

    for subentry in entry.subentries.values():
        if subentry.subentry_type == MASTER_SUBENTRY_TYPE:
            continue

        async_add_entities(
            [
                SchedulerSwitch(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=ENTITY_DESCRIPTIONS[0],
                    subentry=subentry,
                )
            ],
            config_subentry_id=subentry.subentry_id,
        )


class SchedulerSwitch(SchedulerBaseEntity, SwitchEntity):
    """away_scheduler switch class."""

    def __init__(
        self,
        coordinator: SchedulerDatUpdateCoordinator,
        entity_description: SwitchEntityDescription,
        subentry: Any | None = None,
    ) -> None:
        """Initialize the switch class."""
        entity_key = f"switch_{entity_description.key}"
        super().__init__(coordinator, entity_key)
        self.entity_description = entity_description
        self._subentry = subentry

        if subentry is None or subentry.subentry_type == MASTER_SUBENTRY_TYPE:
            registry_id = coordinator.config_entry.entry_id
            device_name = (
                subentry.title
                if subentry is not None
                else coordinator.config_entry.title
            )
        else:
            registry_id = (
                f"{coordinator.config_entry.entry_id}_{subentry.subentry_id}"
            )
            device_name = subentry.title

        self._attr_unique_id = f"{registry_id}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={
                (
                    coordinator.config_entry.domain,
                    registry_id,
                ),
            },
            name=device_name,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self._subentry is None:
            return self.coordinator.config_entry.options.get("scheduler_enabled", True)

        return self._subentry.data.get("scheduler_enabled", True)

    def _enable_switch(self) -> None:
        """Persist the enabled state for the current switch scope."""
        if self._subentry is None:
            entry = self.coordinator.config_entry
            self.hass.config_entries.async_update_entry(
                entry,
                options={
                    **entry.options,
                    "scheduler_enabled": True,
                },
            )
            entry.runtime_data.scheduler_enabled = True
            return

        if self._subentry.subentry_type == MASTER_SUBENTRY_TYPE:
            self.hass.config_entries.async_update_subentry(
                self.coordinator.config_entry,
                self._subentry,
                data={
                    **dict(self._subentry.data),
                    "scheduler_enabled": True,
                },
            )
            self.coordinator.config_entry.runtime_data.scheduler_enabled = True
            return

        subentry = self._subentry
        self.hass.config_entries.async_update_subentry(
            self.coordinator.config_entry,
            subentry,
            data={
                **dict(subentry.data),
                "scheduler_enabled": True,
            },
        )

    def _disable_switch(self) -> None:
        """Persist the disabled state for the current switch scope."""
        if self._subentry is None:
            entry = self.coordinator.config_entry
            self.hass.config_entries.async_update_entry(
                entry,
                options={
                    **entry.options,
                    "scheduler_enabled": False,
                },
            )
            entry.runtime_data.scheduler_enabled = False
            return

        if self._subentry.subentry_type == MASTER_SUBENTRY_TYPE:
            self.hass.config_entries.async_update_subentry(
                self.coordinator.config_entry,
                self._subentry,
                data={
                    **dict(self._subentry.data),
                    "scheduler_enabled": False,
                },
            )
            self.coordinator.config_entry.runtime_data.scheduler_enabled = False
            return

        subentry = self._subentry
        self.hass.config_entries.async_update_subentry(
            self.coordinator.config_entry,
            subentry,
            data={
                **dict(subentry.data),
                "scheduler_enabled": False,
            },
        )

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        self._enable_switch()
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        self._disable_switch()
        self.async_write_ha_state()
