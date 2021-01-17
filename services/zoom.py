import datetime
import logging
import os
import time
import json
import re
import sys
import traceback

import requests
import click
from utils.helper import helper 
from flask.cli import with_appcontext
from utils.zclient import ZoomAPIClient
from config import ZOOM_BASE_URL, ZOOM_API_CLIENT, ZOOM_API_SECRET

logger = logging.getLogger('zoom-dashboard')

def _get_live_events(zoom, meeting, data):
    """
    Iteration to retrieve all events
    """
    events = []
    try: 
        if meeting:
            res = zoom.list_meetings(**data)
            events = res["meetings"]
            counter = 1
            while res["next_page_token"] != '':
                if counter > 9:
                    counter = 1
                    time.sleep(60)
                data["next_page_token"] = res["next_page_token"]
                res = zoom.list_meetings(**data)
                events.extend(res["meetings"])
                counter += 1
        else:
            res=zoom.list_webinars(**data)
            events = res["webinars"]
            counter = 1
            while res["next_page_token"] != '':
                if counter > 9:
                    counter = 1
                    time.sleep(120)
                    logger.warn("We need to go sleep as going above 10 calls")
                data["next_page_token"] = res["next_page_token"]
                res = zoom.list_meetings(**data)
                events.extend(res["webinars"])
                counter += 1
    except requests.exceptions.HTTPError as ex: 
        logger.error(ex)
        time.sleep(60)
        events=None  
    except:
        logger.error("Unexpected exception: {}".format(traceback.format_exc()))  
        time.sleep(60)
        events=None                  
    return events


@click.command()
@click.option("--debug", help='Do some command line printing', is_flag=True)
@click.option("--meeting", help='We are dealing with meetings', is_flag=True)
@click.option("--interval", help='In minutes to iterate', type=int, default=0)
@click.option("--start_date", help='Start date for the report, it always considers just a day e.g. 2020-11-24')
@click.option("--past", help='In case we are interested in past events', is_flag=True)
@with_appcontext
def live_events(meeting, interval, past, start_date, debug):
    """
    Command to retrieve events and participants from Zoom 
    """
    logger.info("Starting script")
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
    typeofevent = 'live'
    if past:
        typeofevent = 'past'
    data = {
        'type': typeofevent,
        'page_size': 300
    }
    
    logger2 = None
    logger3 = None
    arrids = []
    arrparticipants = []
    if meeting and not past:
        logger2 = helper.getFileLogger("zoom-meetings-live.log", "meeting-live")
    elif meeting:
        logger2 = helper.getFileLogger("zoom-meetings-past.log", 'meeting-past')
        arrids = helper.readFileArray("zoom-meetings-past.log")
        logger3 = helper.getFileLogger("zoom-meetings-pasticipants.log", 'meeting-participants-past')
        arrparticipants = helper.readFileArray("zoom-meetings-pasticipants.log")
    elif not meeting and not past:
        logger2 = helper.getFileLogger("zoom-webinars-live.log", "webinar-live")   
    else:
        logger2 = helper.getFileLogger("zoom-webinars-past.log", 'webinar-past')
        arrids = helper.readFileArray("zoom-webinars-past.log")
        logger3 = helper.getFileLogger("zoom-webinars-pasticipants.log", 'webinar-participants-past')
        arrparticipants = helper.readFileArray("zoom-webinars-pasticipants.log")

    while True:
        if start_date:
            if re.match(r'\d{4}-\d{2}-\d{2}', start_date):
                data["from"] = start_date
                data["to"] = start_date
        else:
            if past:
                data["from"] = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d") 
            else:
                check = datetime.datetime.now()
                total_minutes = check.hour * 60 + check.minute
                # if just three hours in the new day lets consider yesterday meetings if any
                if total_minutes < 180:
                    data["from"] = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                else:    
                    data["from"] = datetime.date.today().strftime("%Y-%m-%d") 
            data["to"] = datetime.date.today().strftime("%Y-%m-%d")
        
        if debug: logger.debug(data)
        time.sleep(interval * 60)
        ret = _get_live_events(zoomapi, meeting, data=data.copy())
        if ret == None:
            logger.warn("No values return in this iteration. HTTP Exception")
            continue
        if len(ret)==0 and interval > 0:
            logger.info("No values return in this iteration")
            continue
        if not past:
            sumparticipants = sum(item["participants"] for item in ret)
            sumpstn = sum( 1 for item in ret if item['has_pstn'])
            sumvoip = sum( 1 for item in ret if item['has_voip'])
            sum3partyaudio= sum( 1 for item in ret if item['has_3rd_party_audio'])
            sumvideo = sum( 1 for item in ret if item['has_video'])
            sumscreenshare = sum( 1 for item in ret if item['has_screen_share'])
            sumrecording = sum( 1 for item in ret if item['has_recording'])
            sumsip = sum( 1 for item in ret if item['has_sip'])
            sumvideo = sum( item["in_room_participants"] for item in ret if 'in_room_participants' in item)
            livejson = {
                "type": 'meeting' if meeting else 'webinar',
                "events": len(ret),
                "sumparticipants": sumparticipants,
                "sumpstn": sumpstn,
                "sumvoip": sumvoip,
                "sum3partyaudio": sum3partyaudio,
                "sumscreenshare": sumscreenshare,
                "sumrecording": sumrecording,
                "sumsip": sumsip,
                "sumvideo": sumvideo,
                "start_time": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            logger2.info(json.dumps(livejson))
            if debug:
                logger.info("Total: {} : {}".format('meeting' if meeting else 'webinar', livejson))
        else:
            if debug:
                logger.debug("length of elements in array: {}".format(len(arrids)))
            arrids = helper.cleanArr(arrids) 
            arrparticipants = helper.cleanArr(arrparticipants)
            if debug:
                logger.debug("length of elements in array after cleanup: {}".format(len(arrids)))

            for item in ret:
                if 'duration' in item:
                    item['duration'] = helper.convertStrToSec(item['duration'])
                if item['uuid'] not in arrids:
                    if meeting:
                        item['meeting'] = 1
                    else:
                        item['webinar'] = 1    
                    item['zoomid'] = item.pop('id')    
                    logger2.info(json.dumps(item))
                    arrids[item['uuid']] = item['start_time']
                    if debug:
                        logger.info("{} added to meetings".format(item['uuid']))
                        logger.info(json.dumps(item))
                if item['uuid'] not in arrparticipants and helper.timeDiffinMinutes(item['end_time']) >= 180:
                    ret2 = _get_past_participants_simplified(zoomapi, meeting, item['uuid'])
                    if ret2 == None:
                        logger.warn("No values return in this iteration for participants for uuid: {}".format(item['uuid']))
                        continue
                    for participant in ret2:
                        participant['uuid'] = item['uuid']
                        if 'zoomid' in item:
                            participant['zoomid'] = item['zoomid']
                        else: 
                            participant['zoomid'] = item['id']
                        if 'id' not in participant:
                            participant['participantid'] = 'none'
                        else:    
                            participant['participantid'] = participant.pop('id')
                        if meeting:
                            participant['meeting'] = 1
                        else:
                            participant['webinar'] =1    
                        if "join_time" in participant and "leave_time" in participant:
                            participant['duration'] = (datetime.datetime.strptime(participant["leave_time"], "%Y-%m-%dT%H:%M:%SZ") - \
                                datetime.datetime.strptime(participant["join_time"], "%Y-%m-%dT%H:%M:%SZ")).total_seconds()
                        logger3.info(json.dumps(participant))
                    arrparticipants[item['uuid']] = item['start_time']
                    if debug:
                        logger.info("{} added to participants".format(item['uuid']))

        if interval == 0:
            break
        
def _get_past_participants_simplified(zoom, meeting, uuid):
    """

    Args:
        zoom ([type]): [description]
        meeting ([type]): [description]
    """
    data = {
        'type': 'past',
        'page_size': 300
    }
    if meeting:
        data['meeting_id'] = uuid
    else:
        data['webinarId'] = uuid   
    return _get_past_participants(zoom, meeting, data)

def _get_past_participants(zoom, meeting, data):
    """
    Iteration to retrieve all participants in a event
    """
    events = []
    try: 
        if meeting:
            res = zoom.list_participants_meeting(**data)
            events = res["participants"]
            counter = 1
            while res["next_page_token"] != '':
                if counter > 9:
                    counter = 1
                    time.sleep(60)
                data["next_page_token"] = res["next_page_token"]
                res = zoom.list_participants_meeting(**data)
                events.extend(res["participants"])
                counter += 1
        else:
            res = zoom.list_participants_webinar(**data)
            events = res["participants"]
            counter = 1
            while res["next_page_token"] != '':
                if counter > 9:
                    counter = 1
                    time.sleep(60)
                data["next_page_token"] = res["next_page_token"]
                res = zoom.list_participants_webinar(**data)
                events.extend(res["participants"])
                counter += 1
    except requests.exceptions.HTTPError as ex:
        if ex.errno == 404:
            logger.warn("{} {} is not over?".format('meeting' if meeting else 'webinar', data['meeting_id'] if meeting else data['webinarId']))
        logger.warn(ex)
        events=None 
        time.sleep(60)       
    return events

@click.command()
@click.option("--dry", help='Just output operations without doing it', is_flag=True)
@click.option("--meeting", help='We are dealing with meetings', is_flag=True)
@click.option("--interval", help='In minutes to iterate', type=int, default=0)
@click.option("--eventuuid", help='Event id')
@with_appcontext
def past_participants(dry, meeting, interval, eventuuid):
    """
    Get participants in a past meeting or webinar
    """
    logger.info("Starting script")

    data = {
        'type': 'past',
        'page_size': 300
    }
    
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
    if meeting:
        data['meeting_id'] = eventuuid
    else:
        data['webinarId'] =eventuuid
    
    print(data)

    if not interval:
        ret = _get_past_participants(zoomapi, meeting, data=data)
        print(json.dumps(ret))
        return 
    while interval > 0:
        ret = _get_past_participants(zoomapi, meeting, data=data)
        print(json.dumps(ret))
        time.sleep(interval*60)


@click.command()
@click.option("--dry", help='Just output operations without doing it', is_flag=True)
@click.option("--file", help='File to extract participants')
@click.option("--meeting_id", help='meeting id to do operations on')
@with_appcontext
def add_registrant_onevent(dry, file, meeting_id):
    logger.info("Starting script")
    lines = []
    with open(file, 'r') as reader:
        lines = reader.readlines()

    logger2 = helper.getFileLogger("sailing-club.log")
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
   
    for line in lines:
        arr = line.split(',')
        data = {
            'auto_approve': False,
            'email': arr[3].strip(),
            'first_name': arr[1],
            'last_name': arr[2] 
        }
        print(data)
        res = zoomapi.add_registrant_meeting(meeting_id,**data)
        print(res)
        logger2.info("Email: {} Surname: {}".format(arr[3].strip(), arr[2]))
        logger2.info(res)

def _get_registrants(zoom, meeting, data):
    """
    Iteration to retrieve all registrants in a event
    """
    people = []
    if meeting:
        res = zoom.list_registrants_meeting(**data)
        people = res["registrants"]
        counter = 1
        while res["next_page_token"] != '':
            if counter > 9:
                counter = 1
                time.sleep(60)
            data["next_page_token"] = res["next_page_token"]
            res = zoom.list_registrants_meeting(**data)
            people.extend(res["registrants"])
            counter += 1
    return people
    

@click.command()
@click.option("--dry", help='Just output operations without doing it', is_flag=True)
@click.option("--meeting_id", help='meeting id to do operations on')
@with_appcontext
def list_registrants_onevent(dry, meeting_id):
    logger.info("Starting script")
    
    logger2 = helper.getFileLogger("sailing-club-registrants.log")
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
   
    data = {
        'meeting_id': meeting_id,
        'page_size': 300
    }
    res = _get_registrants(zoomapi, meeting_id, data=data)
    print(res)
    logger2.info(json.dumps(res))

