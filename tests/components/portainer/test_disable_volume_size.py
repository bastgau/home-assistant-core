"""Tests for the option to disable fetching volume sizes in Portainer."""

from unittest.mock import AsyncMock

from pyportainer.models.docker import DockerDFType
import pytest
from pytest_homeassistant.common import MockConfigEntry

from homeassistant.components.portainer.const import CONF_DISABLE_VOLUME_SIZE, DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_TOKEN, CONF_URL, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from . import setup_integration

USER_INPUT = {
    CONF_URL: "https://127.0.0.1:9000/",
    CONF_API_TOKEN: "test_api_token",
    CONF_VERIFY_SSL: True,
}

DISK_USAGE_ENTITY_ID = "sensor.my_environment_image_disk_usage_total_size"
VOLUME_DISK_USAGE_ENTITY_ID = "sensor.my_environment_volume_disk_usage_total_size"
VOLUME_SIZE_ENTITY_ID = "sensor.myvolume_volume_size"


@pytest.fixture(autouse=True)
def enable_all_entities(entity_registry_enabled_by_default: None) -> None:
    """Make sure all entities are enabled."""


async def test_user_flow_disable_volume_size(
    hass: HomeAssistant, mock_portainer_client: AsyncMock
) -> None:
    """Test the option is stored when set during setup."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**USER_INPUT, CONF_DISABLE_VOLUME_SIZE: True}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_DISABLE_VOLUME_SIZE] is True


@pytest.mark.usefixtures("mock_portainer_client", "mock_setup_entry")
async def test_reconfigure_disable_volume_size(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test the option can be changed when reconfiguring."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={**USER_INPUT, CONF_DISABLE_VOLUME_SIZE: True},
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_DISABLE_VOLUME_SIZE] is True


async def test_volume_size_not_fetched_when_disabled(
    hass: HomeAssistant,
    mock_portainer_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test no df request is made and the related sensors are not created."""
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        data={**mock_config_entry.data, CONF_DISABLE_VOLUME_SIZE: True},
    )
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    mock_portainer_client.docker_system_df.assert_not_called()
    assert hass.states.get(DISK_USAGE_ENTITY_ID) is None
    assert hass.states.get(VOLUME_SIZE_ENTITY_ID) is None
    assert hass.states.get(VOLUME_DISK_USAGE_ENTITY_ID) is None


async def test_volume_size_fetched_by_default(
    hass: HomeAssistant,
    mock_portainer_client: AsyncMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test volume sizes are measured when the option is not set."""
    await setup_integration(hass, mock_config_entry)

    mock_portainer_client.docker_system_df.assert_any_call(
        1, data_type=DockerDFType.VOLUME, verbose=True
    )
    assert hass.states.get(VOLUME_SIZE_ENTITY_ID) is not None
