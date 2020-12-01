import logging
import logging.handlers
import json
import os 

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
    def readFileArray(log_file_name):
        """Read a log file and extracts the uuid of all elements, to avoid duplicates

        Args:
            log_file_name (str): Name of the file, it should be absolute, otherwise relative to where 
            this program is running

        Returns:
            list: A list of uuid
        """
        arrids=[]
        if not os.path.exists(log_file_name):
            return arrids
        filelog = open(log_file_name, 'r')
        for line in filelog:
            d = json.loads(line)
            if d['uuid'] not in arrids:
                arrids.append(d['uuid'])
        return arrids

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