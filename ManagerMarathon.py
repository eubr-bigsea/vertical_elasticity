import time
import json
import requests
from requests.auth import HTTPBasicAuth

class ManagerMarathon():

    def __init__ (self, url, user, passw ):
        self.url = url 
        self.auth = HTTPBasicAuth(user, passw)
        self.max_retries = 100

    # Returns JSON with information of a target job
    def getInfo(self, jobName):
        url =  self.url  + '/v2/apps/' + jobName 
        head = { 'Content-type':'application/json; charset=utf-8', 'Accept': 'application/json' }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.get( url, headers = head, auth=self.auth)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok: 
            if (response.status_code == 200):
                info = json.loads(str(response.text ).encode("utf-8"))['app']
                return info
            else:        
                print('ERROR: '+ str(response.status_code) + ' -> ' +jobName + ' does not exist') 
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return {}

    def getInfoAllRunningApps (self):
        url =  self.url  + '/v2/apps/' 
        head = { 'Content-type':'application/json; charset=utf-8', 'Accept': 'application/json' }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.get( url, headers = head, auth=self.auth)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                info = json.loads(str(response.text ) )
                return info
            else:        
                print('ERROR: '+ str(response.status_code) + 'in GET all Running Apps') 
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return {}

    # Adding a Docker Job
    def sendJob(self, job):
        url =  self.url  + '/v2/apps'
        head = { 'Content-type':'application/json; charset=utf-8', 'Accept': 'application/json' }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response =  requests.post( url, headers=head, data=json.dumps(job) , auth=self.auth)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 201):
                print('Successfully created job: ' + job['id'])
                return True
            else:
                print('ERROR: '+ str(response.status_code) + ' when we trying to create a Docker job: ' + job['id'])  
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return False
    # Update a Job
    def updateJob(self, job):
        invalids_keys = ['tasksUnhealthy','tasksStaged','unreachableStrategy','labels','tasks','deployments','version','uris','readinessChecks','tasksRunning','user','killSelection','storeUrls','gpus','versionInfo','tasksHealthy','secrets','ports','residency']
        newjob = {}
        for key in job.keys():
            if not key in invalids_keys:
               newjob[key] = job[key]
        job = newjob
        url =  self.url  + '/v2/apps' + job['id']
        head = { 'Content-type':'application/json; charset=utf-8', 'Accept': 'application/json' }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response =  requests.put( url, headers=head, data=json.dumps(job), auth=self.auth )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                print('Successfully update job: ' + job['id'])
                return True
            else:
                print('ERROR: '+ str(response.status_code) + ' when we trying to update a Docker job: ' + job['id'] + ':\n' + json.loads(str(response.text ).encode("utf-8"))['message'] ) 
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return False

    # Deleting a Job
    def deleteJob(self, jobName):
        url =  self.url  + '/v2/apps/' + jobName  
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response =  requests.request( 'DELETE', url, auth=self.auth )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                print('Successfully deleted job: ' + jobName)
                return True
            else:
                print('ERROR '+ str(response.status_code) + ' when we trying to delete ' + jobName) 
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return False

  