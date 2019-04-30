# -*- coding: utf-8 -*-
"""
@author: AVISIA

"""

""" useful ressources:
    1- multithreading VS multiprocessing :
     * https://blog.usejournal.com/multithreading-vs-multiprocessing-in-python-c7dc88b50b5b 
     * https://stackoverflow.com/questions/3044580/multiprocessing-vs-threading-python
    2- create MongoDb database with python
     * https://www.w3schools.com/python/python_mongodb_getstarted.asp
"""

import requests
import os
import datetime
import time
import concurrent.futures
import json
import pymongo


#Global variables declaration
key ="e5826fa88b702efa628cc63fda458fefc13e1674"
url_station = "https://api.jcdecaux.com/vls/v1/stations?contract=%s&apiKey=%s"
url_contract = 'https://api.jcdecaux.com/vls/v1/contracts?apiKey=%s'
List_contrat ={}

def collecting_data(key=None, contract="amiens", delayms=1000,database= "mydb", outfile="velib_data.json",
                        stop_datetime=None, log_every=10,
                        fLOG=print):
        """
        Collects data for a period of time.
        @param      contract        contract name, @see te _contracts
        @param      delayms         delay between two collections (in ms),  here the update is done every minute
        @param      database        The database name in MongoDB
        @param      outfile         write data in this file (json), if single_file is True, outfile is used as a prefix
        @param      single_file     if True, one file, else, many files with timestamp as a suffix
        @param      stop_datetime   if None, never stops, else stops when the date is reached
        @param      log_every       print something every <log_every> times data were collected
        @param      fLOG            logging function (None to disable)
        @return                     list of created file
        """
        
        #print(contract) # decommenter si tu veux voir comment le threading se passe
        
        delay = datetime.timedelta(seconds=delayms / 1000)
        now = datetime.datetime.now()
        cloc = now
        delayms /= 50
        delays = delayms / 1000.0
        nb = 0 
       
        if database is not None:
           #Create a collection (MongoDB) of the same name as the contract
           mycol = database[contract]
        
        #Treatments
        while stop_datetime is None or now < stop_datetime:
            now = datetime.datetime.now()
            cloc += delay
            js = get_stations(key, contract)
            if outfile is not None:
                #Create JSON files locally: each file contains the latest update
                outfile=outfile % contract
                with open(outfile, "w+", encoding="utf8") as f:
                    f.write("%s\t%s\n" % (str(js)))
           
            if database is not None:
                #Insert data into the contract collection
                mycol.insert_many(js)
            
            nb += 1
            
            #Print information in screen 
            if fLOG and nb % log_every == 0:
                fLOG("collecting_data: nb={0} {1} delay={2}".format(
                    nb, now, delay))

            while now < cloc:
                now = datetime.datetime.now()
                time.sleep(delays)

def get_stations(key, contract):
        """
        Returns the data associated to a contract.
        @param      key             JCDeacaux apiKey
        @param      contract        contract name, @see te _contracts
        @return                     :epkg:`json` string
        """
        data= json.loads("[]")
        memoGeoStation = {} #TODO verifier memoGeoStation
        url = url_station % (contract, key)
             
        try:
            resp = requests.get(url=url)
            data = resp.json() 
        except:
            #TODO  un autre try / except
            print("unable to access url: " + url_station)

        now = datetime.datetime.now()
        
        #Treatements (it is not mandatory)
        for o in data:
            o["number"] = int(o["number"])
            o["banking"] = 1 if o["banking"] == "True" else 0
            o["bonus"] = 1 if o["bonus"] == "True" else 0
            o["bike_stands"] = int(o["bike_stands"])
            o["available_bike_stands"] = int(o["available_bike_stands"])
            o["available_bikes"] = int(o["available_bikes"])
            o["collect_date"] = now
            try:
                ds = float(o["last_update"])
                dt = datetime.datetime.fromtimestamp(ds / 1000)
            except ValueError:
                dt = datetime.datetime.now()
            except TypeError:
                dt = datetime.datetime.now()
            o["last_update"] = dt
            try:
                o["lat"] = float(
                o["position"]["lat"]) if o["position"]["lat"] is not None else None
                o["lng"] = float(
                o["position"]["lng"]) if o["position"]["lng"] is not None else None
            except TypeError as e:
                raise TypeError(
                    "Unable to convert geocode for the following row: %s\n%s" %
                    (str(o), str(e)))
        
            key = contract, o["number"]
            if key in memoGeoStation:
                if o["lat"] == 0 or o["lng"] == 0:
                    o["lat"], o["lng"] = memoGeoStation[key]
                elif o["lat"] != 0 and o["lng"] != 0:
                    memoGeoStation[key] = o["lat"], o["lng"]
        
            del o["position"]
        return data
   

def store_data (locally=True,In_database=True,stop=None):
    
    # Set up contracts list
    try:
        resp = requests.get(url=url_contract  % (key))
        data = resp.json()
        if (resp.status_code == requests.codes.ok):
            List_contrat = { k["name"]for k in data}
        #print('Les contrats disponible sont : \n',List_contrat)
    except:
        print("unable to access url: " + url_contract) 
        exit (0)
        
    outfile =None
    if locally:
        # store the results in JSON format locally : in the folder named `data_velib`
        folder = os.path.abspath("data_velib")
        if not os.path.exists(folder):
            os.makedirs(folder)
        outfile = 'data_velib/ %s.json'

    mydb=None
    if In_database:
        #Connect to mongoDB server
        myclient = pymongo.MongoClient("mongodb://localhost:27017/")
  
        #Create database called "Velib_data" or return it if it exists
        mydb = myclient.Velib_data # !, be careful the dataset is not really created unless you fill it

    #We define the date format
    datetime.datetime(2019, 4, 15, 13, 28, 40, 408420) 
    
    # Multithreading 
    if mydb is not None or outfile is not None:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers= len(List_contrat))
        for x in List_contrat :
            executor.submit(collecting_data, key, contract=x, database= mydb, outfile=outfile,
                            delayms=60000, stop_datetime=stop, log_every=1, fLOG=print)

    #print('collections in Velib_data database', mydb.list_collection_names()) #TODO verifier les collections 
                                #TODO remove above instruction once verified 
    
    


if __name__ == '__main__':
      
    stop = datetime.datetime.now() + datetime.timedelta(minutes=2) #None ==> once testing is done 
    store_data (locally=False,In_database=True,stop=stop )
    
    


