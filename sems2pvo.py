import sys
import os
import json
import pygoodwe
import time
import datetime
from pvoutput import PVOutput
import gzip
import ast

def blockPrint():
    sys.stdout = open(os.devnull, 'w')

# Restore
def enablePrint():
    sys.stdout = sys.__stdout__

def log(msg):
    print('{0}:{1}'.format(datetime.datetime.now(),msg))

class SimGwe():
    def __init__(self, filename):
        self.fp = open(filename, encoding='utf-8')
    
    def getCurrentReadings(self):
        line = self.fp.readline()
        if line != '':
            return ast.literal_eval(line)

class SimPvo():
    def __init__(self, filename):
        self.fp = open(filename, 'wt')

    def addstatus(self, data):
        self.fp.write(str(data)+'\n')

class Sems2Pvo():

    def __init__(self, config):
        self.config = config

        if "simpvofn" in self.config:
            self.pvo = SimPvo(self.config["simpvofn"])
        else:
            self.pvo = PVOutput(self.config['pvoutput']['apikey'], 
                                self.config['pvoutput']['systemid'])
        
        if "simgwefn" in self.config:
            self.gwe = SimGwe(self.config["simgwefn"])
        else: 
            self.gwe = pygoodwe.API(self.config['sems']['system_id'],
                                    self.config['sems']['account'],
                                    self.config['sems']['password'])
        
        if "debugfile" in self.config: 
            self.debugfp = gzip.open(self.config['debugfile']+'.gz', 'w')
 

    def goodwetimeconvert(self, gwtime):
        return time.ctime(gwtime/1000)

    def debug(self, data):
        if hasattr(self, 'debugfp'): 
            self.debugfp.write(bytes(str(data)+'\n','utf-8'))
            self.debugfp.flush()

    def run(self):
        log("Getting data from SEMS")
        sems = self.gwe.getCurrentReadings()
        if sems == None:
            return -1

        self.debug(sems)

        plant = sems['inverter'][0]
        inverter = sems['inverter'][0]['invert_full']
        last_refresh_time = datetime.datetime.strptime(plant['last_refresh_time'], '%m/%d/%Y %H:%M:%S')
        time = datetime.datetime.strptime(plant['time'], '%m/%d/%Y %H:%M:%S')
        t = time.strftime("%H:%M")
        d = time.strftime("%Y%m%d")

        if (inverter['status'] == 1):
            #v1 energy generation
            #SEMS gives cumaltive for the day in 'e_day' with 0.1kWH resolution
            #not worth posting to PVO which can calculate itself

            #v2 power generation
            v2 = inverter['pac'] 
            #v3 energy consumption
            #v4 power consumption
            #v5 temperature
            v5 = inverter['tempperature'] 
            #v6 voltage  
            v6 = inverter['vac1']

            pvodata = { 'd':d, 't':t, 'v2':v2, 'v5':v5, 'v6':v6 }
            if (self.config['updateperiod'] == 0) or (time-last_refresh_time) < datetime.timedelta(minutes=self.config['updateperiod']):
                log("Posting to pvoutput {0}W {1}'C {2}VAC".format(
                    pvodata['v2'], pvodata['v5'], pvodata['v6']))
                blockPrint()
                self.pvo.addstatus(pvodata)
                enablePrint()
            else:
                log("No update since "+plant['last_refresh_time'])
        else:
            log('Inverter has been sleeping since {0} having produced {1}kWH today'.format(
                plant['last_refresh_time'], inverter['eday']))
        return 0

with open('config.json') as configfile:
    log("Parsing configuration")
    config = json.load(configfile)
    log("Initialising")
    sems2pvo = Sems2Pvo(config)
    while sems2pvo.run() >= 0:
        if (config['updateperiod'] > 0):
            t1 = datetime.datetime.now() + datetime.timedelta(minutes=config['updateperiod'])       
            t2 = datetime.datetime(t1.year, t1.month, t1.day, t1.hour, 
                    int(t1.minute / config['updateperiod']) * config['updateperiod'])
            waitsec = (t2-datetime.datetime.now()).total_seconds()
            log("Waiting for {0} seconds".format(int(waitsec))) 
            time.sleep(waitsec)

