import logging
import logging.handlers
import json
import os 
import glob
import time
from datetime import datetime


from config import LOG_DIR

class helper:
    
    @staticmethod
    def getFileLogger(log_file_name, logger_name):
        # set TimedRotatingFileHandler for root
        formatter = logging.Formatter('%(message)s')
        # use very short interval for this example, typical 'when' would be 'midnight' and no explicit interval
        handler = logging.handlers.TimedRotatingFileHandler(os.path.join(LOG_DIR, log_file_name), when='midnight', backupCount=20)
        handler.setFormatter(formatter)
        logger = logging.getLogger(logger_name) # or pass string to give it a name
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        return logger

    @staticmethod
    def readFileArray(log_file_name, delta=2):
        """Read a log file and extracts the uuid of all elements, to avoid duplicates
        Get all files following log_file_name and not older than delta days

        Args:
            log_file_name (str): Name of the file, it should be absolute, otherwise relative to where 
            this program is running
            delta (int): Number of days to analyse

        Returns:
            dict: A dict of uuid:start_time
        """
        hashids = {}
        arrfiles = []
        files = glob.glob(os.path.join(LOG_DIR, "{}*".format(log_file_name)))
        for f in files:
            if os.stat(os.path.join(LOG_DIR,f)).st_mtime > (time.time() - (delta * 86400)):
                filelog = open(os.path.join(LOG_DIR,f), 'r')
                for line in filelog:
                    d = json.loads(line)
                    if d['uuid'] not in hashids:
                        if 'start_time' in d:
                            hashids[d['uuid']] = d['start_time']
                        else:
                            hashids[d['uuid']] = d['join_time']        
        return hashids

    @staticmethod
    def cleanArr(arr ,delta=2):
        """Clean-up. Remove all that older than UTC now - delta days

        Args:
            arr (list): arr of json objects e.g. webinars or meetings
            delta (int): number of days

        Returns:
            list: a list
        """
        #print(arr)
        arr = { k:v for k,v in arr.items() if helper.timeDiffinMinutes(v) < (delta * 24 * 60) }
        #arr[:] = [item for item in arr if helper.timeDiffinMinutes(item["start_time"]) < (delta * 24 * 60) ]
        return arr


    @staticmethod
    def convertStrToSec(duration):
        """To ease calculation convert duration (str) in seconds

        Args:
            duration (str): value in the form of <hours:minutes:seconds> coming from Zoom API
        """
        arr = duration.split(':')
        if len(arr) == 1:
            return int(arr[0])
        elif len(arr) == 2:
            return int(arr[0])*60 + int(arr[1])
        else:
            return int(arr[0])*3600 + int(arr[1])*60 + int(arr[2])

    @staticmethod
    def timeDiffinMinutes(date_string):
        """Returns time in minutes difference between date_string and NOW in UTC.

        Args:
            date_string (string): string in  UTC which difference in time we want to know
        """
        d1 = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%SZ')
        d0 = datetime.utcnow()

        diff = d0 - d1
        return diff.total_seconds()/60      
