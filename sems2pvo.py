import sys
import os
import json
import pygoodwe
import time
from datetime import datetime
from pvoutput import PVOutput

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore
def enablePrint():
    sys.stdout = sys.__stdout__

def log(msg):
    print('{0}:{1}'.format(datetime.now(),msg))

class Sems2Pvo():

    def __init__(self, config):
        self.config = config

        self.pvo = PVOutput(self.config['pvoutput']['apikey'], 
                            self.config['pvoutput']['systemid'])
        self.gwe = pygoodwe.API(self.config['sems']['system_id'],
                                self.config['sems']['account'],
                                self.config['sems']['password'])

    def goodwetimeconvert(self, gwtime):
        return time.ctime(gwtime/1000)

    def run(self):
        log("Getting data from SEMS")
        data = self.gwe.getCurrentReadings()
        if (data['inverter'][0]['status'] == 1):
            active = data['inverter'][0]['invert_full']
            #v1 energy generation
            #v2 power generation
            v2 = active['pac'] 
            #v3 energy consumption
            #v4 power consumption
            #v5 temperature
            v5 = active['tempperature'] 
            #v6 voltage  
            v6 = active['vac1']

            pvodata = { 'v2':v2, 'v5':v5, 'v6':v6 }
            log("Posting to pvoutput")
            blockPrint()
            self.pvo.addstatus(pvodata)
            enablePrint()
        else:
            sleeping = data['inverter'][0]['invert_full']
            log('Inverter has been sleeping since {0} having produced {1}kWH today'.format(
                self.goodwetimeconvert(sleeping['last_time']), sleeping['eday']))

with open('config.json') as configfile:
    log("Parsing configuration")
    config = json.load(configfile)
    log("Initialising")
    sems2pvo = Sems2Pvo(config)
    while True:
        sems2pvo.run()
        time.sleep(config['updateperiod']*60)
