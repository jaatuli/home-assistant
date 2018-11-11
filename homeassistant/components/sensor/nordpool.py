import logging
import requests
from datetime import datetime, timedelta

# Import the HA device class from the component that you want to support
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.const import (CONF_DISPLAY_OPTIONS, CONF_UNIT_OF_MEASUREMENT, CONF_NAME, ATTR_ATTRIBUTION)

DOMAIN = 'nordpool'
REQUIREMENTS = ['requests']
DEPENDENCIES = []
SCAN_INTERVAL = timedelta(minutes=10)

_LOGGER = logging.getLogger(__name__)
_RESOURCE = 'https://www.vattenfall.fi/api/price/spot/'

DEFAULT_NAME = 'Nordpool'
ICON = 'mdi:flash'

CONF_AREA = 'area'
CONF_UNIT_OF_MEASUREMENT = 'c/kwh'
CONF_ATTRIBUTION = 'Data provided by Vattenfall'
#TODO: add hour offset setting
#TODO: setting to add VAT to price

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_AREA, default='fi'): cv.string
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the nordpool platform."""
    _LOGGER.debug("Adding component: nordpool ...")

    url = _RESOURCE
    payload = {'lang':config.get(CONF_AREA)}
    uom = CONF_UNIT_OF_MEASUREMENT

    # Add devices
    add_devices([Nordpool(config.get(CONF_NAME), url, payload, uom)])

class Nordpool(Entity):
    def __init__(self, name, url, payload, uom):
        """Initialize the component."""
        self._name = name
        self._url = url
        self._payload = payload
        self._unit_of_measurement = uom
        self._state = None
        self._data = None
        self.update()
        
    @property
    def name(self):
        """Return the display name."""
        return self._name

    @property
    def state(self):
        '''Return the state of the sensor.'''
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return self._unit_of_measurement

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return ICON

    def get_data(self):
        """Fetch data from web and same to memory"""

        today = datetime.today()
        period = today.date().isoformat() + '/' + today.date().isoformat()
        
        r = requests.get(self._url + period, params=self._payload)

        if r.status_code == 200:

            _LOGGER.debug('Status OK: ' + str(r.status_code))
            self._data = r.json()
            return True    
            
        else:
            _LOGGER.error('Could not get data, HTTP status:' + str(r.status_code))
            return False


    def set_price(self):
        """"Set current price for the hour"""

        if self._data == None:
            _LOGGER.debug('Tried to set price with no data')
            return False

        i = 0
        while i < len(self._data):

            today = datetime.today()
            d = datetime.strptime(self._data[i]['timeStamp'], '%Y-%m-%dT%H:%M:%S')
        
            if d.hour == today.hour and d.day == today.day:

                _LOGGER.debug('Price on ' + d.isoformat() + ' is ' + str(self._data[i]['value']))
                self._state = self._data[i]['value']
                return True

            i += 1
        
        return False


    def update(self):
        """Update is polled on init and SCAN_INTERVAL"""
        
        # Check existing data and try to set current price
        if self.set_price():
            return True
        
        # If failed get new data and try again
        elif self.get_data():
            if self.set_price():
                return True
            else:
                _LOGGER.error('Could not set the price')
                return False