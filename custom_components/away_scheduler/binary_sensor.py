"""Binary sensor platform for away_scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo

from .entity import SchedulerBaseEntity
from .const import MASTER_SUBENTRY_TYPE

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SchedulerDatUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="away_scheduler",
        name="Away Scheduler Binary Sensor",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary_sensor platform."""
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
            AwaySchedulerBinarySensor(
                coordinator=entry.runtime_data.coordinator,
                entity_description=ENTITY_DESCRIPTIONS[0],
                subentry=master_subentry,
            )
        ],
        config_subentry_id=master_subentry.subentry_id,
    )


class AwaySchedulerBinarySensor(SchedulerBaseEntity, BinarySensorEntity):
    """away_scheduler binary_sensor class."""

    def __init__(
        self,
        coordinator: SchedulerDatUpdateCoordinator,
        entity_description: BinarySensorEntityDescription,
        subentry: Any | None = None,
    ) -> None:
        """Initialize the binary_sensor class."""
        super().__init__(coordinator, f"binary_sensor_{entity_description.key}")
        self.entity_description = entity_description
        self._subentry = subentry

        if subentry is not None:
            self._attr_device_info = DeviceInfo(
                identifiers={
                    (
                        coordinator.config_entry.domain,
                        coordinator.config_entry.entry_id,
                    ),
                },
                name=subentry.title,
            )

    @property
    def is_on(self) -> bool:
        """Return true if the binary_sensor is on."""
        return (self.coordinator.data or {}).get("title", "") == "foo"
