import sys
import os
import json
import pygoodwe
import time
import datetime
from pvoutput import PVOutput

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore
def enablePrint():
    sys.stdout = sys.__stdout__

def log(msg):
    print('{0}:{1}'.format(datetime.datetime.now(),msg))

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

        #workaround bug in library
        hour = int(datetime.datetime.now().strftime("%H"))
        minute = int(datetime.datetime.now().strftime("%M"))
        t = datetime.time(hour=hour, minute=minute).strftime("%H:%M")

        if (data['inverter'][0]['status'] == 1):
            active = data['inverter'][0]['invert_full']

            #v1 energy generation
            #SEMS gives cumaltive for the day in 'e_day' with 0.1kWH resolution
            #not worth posting to PVO which can calculate itself

            #v2 power generation
            v2 = active['pac'] 
            #v3 energy consumption
            #v4 power consumption
            #v5 temperature
            v5 = active['tempperature'] 
            #v6 voltage  
            v6 = active['vac1']

            pvodata = { 't':t, 'v2':v2, 'v5':v5, 'v6':v6 }
            log("Posting to pvoutput {0}W {1}'C {2}VAC".format(
                pvodata['v2'], pvodata['v5'], pvodata['v6']))
            blockPrint()
            self.pvo.addstatus(pvodata)
            enablePrint()
        elif (data['inverter'][0]['status'] == 0):
            waiting = data['inverter'][0]['invert_full']
            log('Inverter is waiting')
            pvodata = { 't':t, 'v2':0 }
            log("Posting to pvoutput {0}W ".format(pvodata['v2']))
            blockPrint()
            self.pvo.addstatus(pvodata)
            enablePrint()
        else:
            sleeping = data['inverter'][0]['invert_full']
            log('Inverter has been sleeping status={0} since {1} having produced {2}kWH today'.format(
                sleeping['status'], self.goodwetimeconvert(sleeping['last_time']), sleeping['eday']))

with open('config.json') as configfile:
    log("Parsing configuration")
    config = json.load(configfile)
    log("Initialising")
    sems2pvo = Sems2Pvo(config)
    while True:
        t1 = datetime.datetime.now() + datetime.timedelta(minutes=config['updateperiod'])       
        t2 = datetime.datetime(t1.year, t1.month, t1.day, t1.hour, 
                int(t1.minute / config['updateperiod']) * config['updateperiod'])
        waitsec = (t2-datetime.datetime.now()).total_seconds()
        log("Waiting for {0} seconds".format(int(waitsec))) 
        time.sleep(waitsec)
        sems2pvo.run()
