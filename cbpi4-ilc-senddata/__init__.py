# -*- coding: utf-8 -*-
import os
from aiohttp import web
import logging
from unittest.mock import MagicMock, patch
import asyncio
import random

import requests
import time

from cbpi.api import *
from cbpi.api.config import ConfigType
from cbpi.api.dataclasses import Kettle, Props, Step, Fermenter
from cbpi.api.property import Property, PropertyType
from cbpi.api.base import CBPiBase

logger = logging.getLogger(__name__)

@parameters([Property.Kettle(label="Kettle"),
             Property.Select(label="Data",options=["TargetTemp","Power"],description="Select kettle data to be monitored"),
             Property.Text(label="IP ILC", configurable=True, description="IP Adress of ILC SPS (example: 192.168.1.150)", default_value="192.168.1.151"),
             Property.Text(label="Write Variable", configurable=True, description="Write Variable in SPS", default_value="CBPI4.ILC_Write_Variable")])
class ILCSendData(CBPiSensor):
    
    def __init__(self, cbpi, id, props):
        super(ILCSendData, self).__init__(cbpi, id, props)
        self.value = self.value_old = 0
        self.kettle_controller : KettleController = cbpi.kettle
        self.kettle_id=self.props.get("Kettle")
        self.SensorType=self.props.get("Data","TargetTemp")
        self.log_data(self.value)
        self.request_session = requests.Session()
        self.variable_ilc_read = self.props.get("Write Variable")       
        self.ip_ilc = self.props.get("IP ILC")
        self.url = ""

    async def run(self):
        value=0
        counter = 15 # equal to  ~ 30 seconds with sleep(2)
        while self.running is True:
            try:
                self.kettle = self.kettle_controller.get_state()
            except:
                self.kettle = None
            if self.kettle is not None:
                for kettle in self.kettle['data']:
                    if kettle['id'] == self.kettle_id:
                        if self.SensorType == "TargetTemp":
                            current_value = int(kettle['target_temp'])
                            value = current_value
                            #url = "http://" + self.ip_ilc + "/cgi-bin/writeVal.exe?" + self.variable_ilc + "+" + value
                        else:
                            heater = kettle['heater']
                            kettle_heater = self.cbpi.actor.find_by_id(heater)
                            try:
                                state=kettle_heater.instance.state
                            except:
                                state = False
                            if state == True:
#                                logging.info("Instance: {}".format(state))
#                                logging.info(kettle_heater)
                                value = int(kettle_heater.power)
                                #url = "http://" + self.ip_ilc + "/cgi-bin/writeVal.exe?" + self.variable_ilc + "+" + value
                        if counter == 0:
                            if value != 0:
                                self.value=value
                                self.log_data(self.value)
                                self.push_update(self.value)
                                self.value_old=self.value
                                #response = self.request_session.get(url)
                            counter = 15
                        else:
                            if value != self.value_old:
                                self.value=value
                                self.log_data(self.value)
                                self.push_update(self.value)
                                self.value_old=self.value
                                #response = self.request_session.get(url)
                                counter = 15
            self.push_update(self.value,False)
            self.url = "http://" + self.ip_ilc + "/cgi-bin/writeVal.exe?" + self.variable_ilc + "+" + self.value
            #self.cbpi.ws.send(dict(topic="sensorstate", id=self.id, value=self.value))
            counter -=1
            await asyncio.sleep(2)
    
    def get_state(self):
        return dict(value=self.value)

def setup(cbpi):
    cbpi.plugin.register("ILCSendData", ILCSendData)
    pass
