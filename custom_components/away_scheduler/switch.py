"""Switch platform for away_scheduler."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN, MASTER_SUBENTRY_TYPE
from .entity import SchedulerBaseEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigSubentry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import SchedulerDatUpdateCoordinator
    from .data import IntegrationBlueprintConfigEntry

ENTITY_DESCRIPTIONS = (
    SwitchEntityDescription(
        key="away_scheduler",
        name="Away Scheduler",
        icon="mdi:calendar-clock",  # mdi:format-quote-close war vermutlich ein Platzhalter?
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,  # noqa: ARG001 Unused function argument: `hass`
    entry: IntegrationBlueprintConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch platform."""

    master_subentry = next(
        (sub for sub in entry.subentries.values() if sub.subentry_type == MASTER_SUBENTRY_TYPE),
        None,
    )

    if master_subentry is not None:
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
        if subentry.subentry_type != "scheduler_group":
            continue

        devices: list[str] = subentry.data.get("devices", [])
        entities_to_add = []

        for entity_id in devices:
            entities_to_add.append(
                SchedulerSwitch(
                    coordinator=entry.runtime_data.coordinator,
                    entity_description=ENTITY_DESCRIPTIONS[0],
                    subentry=subentry,
                    target_entity_id=entity_id,
                )
            )

        if entities_to_add:
            async_add_entities(entities_to_add, config_subentry_id=subentry.subentry_id)


class SchedulerSwitch(SchedulerBaseEntity, SwitchEntity):
    """away_scheduler switch class."""

    def __init__(
        self,
        coordinator: SchedulerDatUpdateCoordinator,
        entity_description: SwitchEntityDescription,
        subentry: ConfigSubentry,
        target_entity_id: str | None = None,
    ) -> None:
        """Initialize the switch class."""
        self._subentry = subentry
        self._target_entity_id = target_entity_id

        if target_entity_id:
            entity_key = f"{entity_description.key}_{subentry.subentry_id}_{target_entity_id}"
            friendly_name = target_entity_id.split(".")[-1].replace("_", " ").title()
            device_name = f"{subentry.data.get('name', subentry.title)} - {friendly_name}"

            device_identifier = (DOMAIN, f"{subentry.subentry_id}_{target_entity_id}")
        else:
            entity_key = f"{entity_description.key}_{subentry.subentry_id}"
            device_name = subentry.title
            device_identifier = (DOMAIN, coordinator.config_entry.entry_id)

        super().__init__(coordinator, entity_key)
        self.entity_description = entity_description

        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{entity_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={device_identifier},
            name=device_name,
        )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        if self._target_entity_id:
            device_states = self._subentry.data.get("device_states", {})
            return device_states.get(self._target_entity_id, True)

        return self._subentry.data.get("scheduler_enabled", True)

    def _update_switch_state(self, state: bool) -> None:
        """Persist the state change inside the subentry options/data."""
        entry = self.coordinator.config_entry

        if self._target_entity_id:
            current_states = dict(self._subentry.data.get("device_states", {}))
            current_states[self._target_entity_id] = state

            self.hass.config_entries.async_update_subentry(
                entry,
                self._subentry,
                data={
                    **dict(self._subentry.data),
                    "device_states": current_states,
                },
            )
        else:
            self.hass.config_entries.async_update_subentry(
                entry,
                self._subentry,
                data={
                    **dict(self._subentry.data),
                    "scheduler_enabled": state,
                },
            )

            if self._subentry.subentry_type == MASTER_SUBENTRY_TYPE:
                entry.runtime_data.scheduler_enabled = state

    async def async_turn_on(self, **_: Any) -> None:
        """Turn on the switch."""
        self._update_switch_state(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **_: Any) -> None:
        """Turn off the switch."""
        self._update_switch_state(False)
        self.async_write_ha_state()