import logging
import requests
from requests.exceptions import HTTPError

from config import KEYCLOAK_API_TOKEN_ENDPOINT, KEYCLOAK_ENDPOINT, AUTHZSVC_ENDPOINT, CLIENT_SECRET, CLIENT_ID, AUTHZ_ENDPOINT

logger = logging.getLogger('zoom-dashboard')

class Openid:
    def __init__(self):
        token_resp = requests.post(
            KEYCLOAK_API_TOKEN_ENDPOINT,
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "audience" : "authorization-service-api"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        self.token=token_resp.json()['access_token']
        
    
        
    def get_group_id(self, group):
        my_group = requests.get(
            "{0}Group/{1}".format(AUTHZSVC_ENDPOINT,group),
            headers={
            "Authorization": "Bearer {}".format(self.token),
            }
        )
        return my_group.json()["data"]["id"]
    
    def get_identity(self, zoomaccount):
        """Retrieve the id link to a upn.

        Args:
            zoomaccount ([string]): e.g. zsub01

        Returns:
            [string]: [id]
        """
        response = requests.get(
            "{0}Identity/{1}".format(AUTHZSVC_ENDPOINT, zoomaccount),
            headers={
            "Authorization": "Bearer {}".format(self.token),
            }
        ) 
        if response.status_code == 200:
            logger.info('identity {} for account {}'.format(response.json()['data']['id'], zoomaccount))
            return response.json()['data']['id']
        else:
            logger.warn('we couldnt retrieve identity for {} error: {}'.format(zoomaccount, response.reason))
        return None
    
    def add_id_to_group(self, groupid, identity):
        response = requests.post(
            "{0}Group/{1}/memberidentities?ids={2}".format(AUTHZSVC_ENDPOINT, groupid, identity),
            headers={
            "Authorization": "Bearer {}".format(self.token),
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn('identity: {} couldnt be added to group: {} reason: {} http code:'.format(identity, groupid, response.reason, response.status_code))
            raise HTTPError("Unexpected status code {} - {}".format(response.status_code, response.json()))
        
    def remove_id_from_group(self, groupid, identity):
        response = requests.delete(
            "{0}Group/{1}/memberidentities?ids={2}".format(AUTHZSVC_ENDPOINT, groupid, identity),
            headers={
            "Authorization": "Bearer {}".format(self.token),
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warn('identity: {} couldnt be added to group: {} reason: {} http code: {}'.format(identity, groupid, response.reason, response.status_code))
            raise HTTPError("Unexpected status code {} - {}".format(response.status_code, response.json()))


    def get_allmembers(self, groupid, members, fields=None, url=None):
        if not url:
            url= "{0}Group/{1}/memberidentities".format(AUTHZSVC_ENDPOINT,groupid)
        else:
            urlparts=url.split('Group')
            url="{0}Group{1}".format(AUTHZSVC_ENDPOINT,urlparts[1])
            logger.debug("url is {}".format(url))     

        if fields:
            toadd=''
            for item in fields:
                if not toadd:
                    toadd='field={}'.format(item)
                    continue
                toadd += '&field={}'.format(item)
            url='{0}?{1}'.format(url,toadd)

        response = requests.get(
            url,
            headers={
            "Authorization": "Bearer {}".format(self.token),
            }
        )
        if response.status_code == 200:
            for item in response.json()['data']:
                members.append(item)
        if response.json()['pagination']['links']['next']:
            logger.debug("next link: {}".format(response.json()['pagination']['links']['next']))
            self.get_allmembers(groupid,members,url=response.json()['pagination']['links']['next'])
        return