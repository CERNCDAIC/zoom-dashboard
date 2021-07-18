import datetime
import logging
import time
import traceback

import requests
import click

from utils.helper import helper 
from flask.cli import with_appcontext
from utils.zclient import ZoomAPIClient
from utils.openid import Openid
from config import ZOOM_BASE_URL, ZOOM_API_CLIENT, ZOOM_API_SECRET, KEYCLOAK_API_TOKEN_ENDPOINT, KEYCLOAK_ENDPOINT, AUTHZSVC_ENDPOINT, CLIENT_SECRET, CLIENT_ID, AUTHZ_ENDPOINT

logger = logging.getLogger('zoom-dashboard')


@click.command()
@click.option("--sub", help='It is Zoom subaccount', is_flag=True)
@click.option("--group500", help='people with 500 Webinar add-on')
@click.option("--group1000", help='people with 1000 Webinar add-on')
@click.option("--days", help='number of days to be removed from license owner', type=int, default=30)
@with_appcontext
def global_action(sub, group500, group1000, days):

    openid = Openid()
    groupid500=openid.get_group_id(group500)
    logger.info('{} id is: {}'.format(group500, groupid500))
    groupid1000=openid.get_group_id(group1000)
    logger.info('{} id is: {}'.format(group1000, groupid1000))

    members1000=[]
    openid.get_allmembers(groupid1000, members1000, fields=['primaryAccountEmail','upn'])
    members500=[]
    openid.get_allmembers(groupid500, members500, fields=['primaryAccountEmail','upn'])

    for member in members1000:
        print(member)
        zaccount='{}@cernch'.format(member['upn'])
        if sub:
            zaccount=member['primaryAccountEmail']
        try: 
            if _list_webinars(zaccount):
                continue
        except requests.exceptions.HTTPError as ex:
            logger.debug("Could not retrieve webinars for {} exception: {}".format(zaccount, ex))
            continue
    
        #remove from group 1000 and add to 500
        logger.debug('{} needs to be removed from: {}'.format(member['upn'], group1000))
       
        account_id=openid.get_identity(member['upn'])
        if next((item for item in members1000 if item['upn'] == member['upn']), None):
            openid.remove_id_from_group(groupid1000, account_id)
            logger.debug("{} account removed from group {}".format(member['upn'], group1000))
        if not next((item for item in members500 if item['upn'] == member['upn']), None):
            openid.add_id_to_group(groupid500,account_id)
            logger.debug("{} account added to group {}".format(member['upn'], group500))
        else:
            logger.debug("{} already a member of group {}".format(member['upn'], group500))
            _set_zoom_webinar(zaccount, 500)
    
    lastwebinar=_last_zoom_webinar('past', 6)
    for member in members500:
        zaccount='{}@cernch'.format(member['upn'])
        if sub:
            zaccount=member['primaryAccountEmail']
        if (datetime.datetime.now() - datetime.datetime.strptime(lastwebinar.get('zaccount', datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")) , "%Y-%m-%dT%H:%M:%SZ")).days > days:
            account_id=openid.get_identity(member['upn'])
            logger.debug("UPN: {} identity: {}".format(member['upn'], account_id))
            openid.remove_id_from_group(groupid500, account_id)
            logger.debug("{} account removed from group {}".format(member['upn'], group500))
            # change webinar add-on
            _set_zoom_webinar(zaccount, 0)


@click.command()
@click.option("--group", help='group to retrieve members from')
@click.option("--account", help='Zoom account to be added e.g. toto@cern.ch')
@with_appcontext
def get_members_add_member(group, account):
    
    openid = Openid()
    
    groupid=openid.get_group_id(group)
    members = []
    openid.get_allmembers(groupid, members)
    logger.debug("members length {}".format(len(members)))

    #find identity for account
    if account:
        account_parts=account.split('@')
        account_id=openid.get_identity(account_parts[0])
        if not next((member for member in members if member['upn'] == account_parts[0]), None):
            openid.add_id_to_group(groupid,account_id)
            logger.debug("{} account added to group {}".format(account_parts[0], group))
        else:
            logger.debug("{} already a member of group {}".format(account_parts[0], group))
    

@click.command()
@click.option("--user", help='Zoom user to retrieve webinars')
@with_appcontext
def list_webinars(user):
    logger.info("Starting script")

    return _list_webinars(user)

def _list_webinars(user):
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
    data = {
        'page_size': 300,
        'id': user
    }
    ret = zoomapi.list_user_webinars(**data)
    for item in ret['webinars']:
        print(item)
        if item['type'] == 5  and datetime.datetime.strptime(item['start_time'], "%Y-%m-%dT%H:%M:%SZ") > datetime.datetime.now():
            print('got here')
            if ('1000attendees' in item.get('agenda', '') or '1000attendees' in item.get('topic', '')):
                print(item)  
                return True
        elif item['type'] == 9:
            webinarobj = zoomapi.get_webinar_details(**{'webinarid': item['id']})
            for oc in webinarobj.get('occurrences', None):
                if datetime.datetime.strptime(oc['start_time'], "%Y-%m-%dT%H:%M:%SZ") > datetime.datetime.now() and \
                    ('1000attendees' in item.get('agenda', '') or '1000attendees' in item.get('topic', '')):
                    print(webinarobj)
                    return True               

    return False

@click.command()
@click.option("--past", help='if present its about past webinars', is_flag=True)
@click.option("--interval", help='number of months', type=int)
@with_appcontext
def last_zoom_webinar(past, interval):
    logger.info("Starting script")
    return _last_zoom_webinar(past,interval)
    

def _last_zoom_webinar(past, interval):
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)

    lastwebinar={}
    if past:
        typeofevent = 'past'
    else:
        typeofevent = 'live'
    data = {
        'type': typeofevent,
        'page_size': 300
    }    

    while interval > 0:
        data['from']=(datetime.date.today() - datetime.timedelta(days=interval*30)).strftime("%Y-%m-%d")
        if interval == 0:
            data['to']=datetime.date.today().strftime("%Y-%m-%d")
        else:
            data['to']=(datetime.date.today() - datetime.timedelta(days=(interval-1)*30)).strftime("%Y-%m-%d")
        print(data['from'])
        print(data['to'])
        ret = _get_live_events(zoomapi, data=data.copy())
        interval=interval-1
        if ret == None or len(ret)==0:
            logger.warn("No values return in this iteration. HTTP Exception")
            continue

        for item in ret:
            print(item)
            if 'end_time' in item.keys():
                if item['email'] in lastwebinar.keys():
                    if datetime.datetime.strptime(item["end_time"], "%Y-%m-%dT%H:%M:%SZ") > \
                    datetime.datetime.strptime(lastwebinar[item['email']], "%Y-%m-%dT%H:%M:%SZ"):
                        lastwebinar[item['email']] = item['end_time']
                else:
                    lastwebinar[item['email']] = item['end_time']
        logger.info("total number of entries retrieved from: to: value: {}".format(data['from'], data['to'],len(ret)))
    print(lastwebinar)
    return  lastwebinar

def _get_live_events(zoom, data):
    """
    Iteration to retrieve all events
    """
    events = []
    try: 
        res=zoom.list_webinars(**data)
        events = res["webinars"]
        counter = 1
        while res["next_page_token"] != '':
            if counter > 9:
                counter = 1
                time.sleep(120)
                logger.warn("We need to go sleep as going above 10 calls")
            data["next_page_token"] = res["next_page_token"]
            res = zoom.list_webinars(**data)
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
@click.option("--account", help='id of the account to get')
@click.option("--capacity", help='webinar capacity', type=int)
@with_appcontext
def set_zoom_webinar(account, capacity):
    """[summary]

    Args:
        account ([string]): id of the account e.g. email or id
        capacity ([int]): capacity of the webinar, if > 0 it will be set
    """
    logger.info("Starting script")
    _set_zoom_webinar(account, capacity)
    
    

def _set_zoom_webinar(account, capacity):
    zoomapi = ZoomAPIClient(ZOOM_API_CLIENT, ZOOM_API_SECRET, ZOOM_BASE_URL)
    logger.info("working with account: <{}>".format(account))
    data = {}
    if capacity > 0 and capacity in [500, 1000]:
        data = {            
            "id": account,
            "feature": {
                "webinar": True,
                "webinar_capacity": capacity
            }
        }
    else:
        data = {            
            "id": account,
            "feature": {
                "webinar": False,
            }
        }
    result = zoomapi.set_webinar_addon(**data)
    if result.status_code == 204:
        logger.info('User: {} was updated'.format(account))
    else:
        logger.error('User: {} couldnt be found. Error: {}'.format(account, result))