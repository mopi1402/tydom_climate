"""
Adds support for the Essent Icy E-Thermostaat units.
For more details about this platform, please refer to the documentation at
https://github.com/custom-components/climate.e_thermostaat
"""
import logging
import requests
import voluptuous as vol
import time

from .tydum_api import system_info, set_temp, set_hvac_mode

from homeassistant.components.climate import ClimateDevice, PLATFORM_SCHEMA
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT, PRESET_AWAY, PRESET_COMFORT, PRESET_HOME, PRESET_SLEEP,
    SUPPORT_PRESET_MODE, SUPPORT_TARGET_TEMPERATURE, CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE)
from homeassistant.const import (
    ATTR_TEMPERATURE, CONF_USERNAME, CONF_PASSWORD, TEMP_CELSIUS)
import homeassistant.helpers.config_validation as cv

__version__ = '0.0.1'

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Tydom Climate'

STATE_COMFORT = "Comfort"
STATE_BOOST = "Boost"
STATE_AWAY = "Away"
STATE_ECO = "Economic"


MIN_TEMP = 12
MAX_TEMP = 30

SUPPORT_FLAGS = SUPPORT_PRESET_MODE | SUPPORT_TARGET_TEMPERATURE |
SUPPORT_PRESET = [STATE_COMFORT, STATE_BOOST, STATE_AWAY, STATE_ECO]

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Optional(CONF_AWAY_TEMPERATURE, default=DEFAULT_AWAY_TEMPERATURE):
        vol.Coerce(float),
    vol.Optional(CONF_SAVING_TEMPERATURE, default=DEFAULT_SAVING_TEMPERATURE):
        vol.Coerce(float),
    vol.Optional(CONF_COMFORT_TEMPERATURE,
                 default=DEFAULT_COMFORT_TEMPERATURE): vol.Coerce(float)
})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the Tydom Platform."""
    name = config.get(CONF_NAME)
    comfort_temp = config.get(CONF_COMFORT_TEMPERATURE)
    saving_temp = config.get(CONF_SAVING_TEMPERATURE)
    away_temp = config.get(CONF_AWAY_TEMPERATURE)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    add_entities([TydomClimate(
        name, username, password,
        comfort_temp, saving_temp, away_temp)])

class TydomClimate(ClimateDevice):
    """Representation of a E-Thermostaat device."""

    def __init__(self, name, username, password,
                 comfort_temp, saving_temp, away_temp):
        """Initialize the thermostat."""
        self._name = name
        self._username = username
        self._password = password

        self._comfort_temp = comfort_temp
        self._saving_temp = saving_temp
        self._away_temp = away_temp

        self._current_temperature = None
        self._target_temperature = None
        self._old_conf = None
        self._current_operation_mode = None

        self._device_id = None
        self._data = None

        self.update()

    @property
    def payload(self):
        """Return the payload."""
        return {'username': self._username, 'password': self._password}

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID for this thermostat."""
        return '_'.join([self._name, 'climate'])

    @property
    def should_poll(self):
        """Polling is required."""
        return True

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return MIN_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return MAX_TEMP

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def hvac_mode(self):
        """Return hvac operation ie. heat, cool mode."""
        if self._data['authorization'] == 'STOP':
            return HVAC_MODE_OFF
        elif self._data['authorization'] == 'HEATING':
            return HVAC_MODE_HEAT
        return None

    @property
    def hvac_modes(self):
        """HVAC modes."""
        return [HVAC_MODE_OFF, HVAC_MODE_HEAT]

    @property
    def hvac_action(self):
        """Return the current running hvac operation."""
        if self._data['authorization'] == 'STOP':
            return CURRENT_HVAC_OFF
        elif self._data['authorization'] == 'HEATING':
            return CURRENT_HVAC_HEAT
        return None

    @property
    def preset_mode(self):
        """Return the current preset mode, e.g., home, away, temp."""
        return self._current_operation_mode

    @property
    def preset_modes(self):
        """Return a list of available preset modes."""
        return SUPPORT_PRESET

    @property
    def is_away_mode_on(self):
        """Return true if away mode is on."""
        return self._current_operation_mode in [STATE_AWAY]

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    def set_preset_mode(self, preset_mode: str):
        """Set new preset mode."""
        STATE_COMFORT, STATE_BOOST, STATE_AWAY, STATE_ECO

        if preset_mode == STATE_COMFORT:
            self._set_temperature(self.21.50)
        elif preset_mode == STATE_ECO:
            self._set_temperature(self.19)
        elif preset_mode == STATE_AWAY:
            self._set_temperature(self.15)
        elif preset_mode == STATE_BOOST:
            self._set_temperature(30)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._set_temperature(temperature)

    def _set_temperature(self, temperature):
        """Set new target temperature, via URL commands."""
        self._target_temperature = temperature
        set_temp(self._device_id, temperature, self.payload)

    def _get_data(self):
        """Get the data of the Tydom."""
        self._data = system_info(self.payload)
        if self._data:
            self._target_temperature = data['setpoint']
            self._current_temperature = data['temperature']
            self._current_operation_mode = data['authorization']
            self._device_id = data['endpoint']
            _LOGGER.debug("Tydum value: {}".format(self._data))
        else:
            _LOGGER.error("Could not get data from Tydum. {}".format(self._data))

    def update(self):
        """Get the latest data."""
        self._get_data()
