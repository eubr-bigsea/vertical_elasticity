import time
import json
import requests

class ManagerMonasca():

    def __init__(self, auth_url, username, password, project_name, monclient_url ):
        self.auth_url = auth_url + '/v3/' + 'auth/tokens'
        self.username = username
        self.password = password
        self.project_name = project_name
        self.monclient_url = monclient_url
        self.token = self.request_token()
        self.max_retries = 100

    def checkAlarm(self, alarm):
        ok_keys = [ 'name', 'severity', 'description', 'expression', 'ok_actions', 'alarm_actions', 'undetermined_actions', 'match_by' ]         
        for key in alarm.keys():
            if not key in ok_keys:
                return False
        return True

    def checkMetric(self, metric):
        ok_keys = [ 'name', 'dimensions', 'value', 'timestamp', 'value_meta' ]        
        for key in metric.keys():
            if not key in ok_keys:
                return False
        return True

    def delete_alarm(self, alarm_id):
        url = self.monclient_url + '/v2.0/alarm-definitions/' + str(alarm_id) #'0b8ac632-4c1d-477b-9975-c66f4a1ebf9e'
       	head = { 'X-Auth-Token': self.token }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.delete( url, headers=head)
                ok = True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 204):
                print('Successfully deleted alarm with ID ' + alarm_id)
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                response = self.delete_alarm(alarm_id)
            else:
                print('ERROR ' + str(response.status_code) + ' when we trying to delete alarm with ID '+ alarm_id)
        else:
            print('ERROR: Cannot connect to ' + url + '. Alarm not deleted.') 
        return response	

    def request_token (self):
        payload = {'auth':{'identity':{'methods':['password'],'password':{'user':{'name':self.username,'domain':{'id':'default'},'password':self.password}}},'scope':{'project':{'name':self.project_name,'domain':{'id':'default'}}}}}
        head = { 'Content-type':'application/json' }
        msg = json.dumps(payload)
        print('Requesting token...')
        ok = False
        token = ''
        response = ''
        while not ok:
	        try:
		        response = requests.post( self.auth_url , headers=head, data=msg )               
		        token = str( response.headers['X-Subject-Token'] )
		        ok = True
	        except requests.exceptions.ConnectionError:
		        print (url + ': Connection refused, waiting 5 seconds') 
		        time.sleep(5)
        if (ok):		
	        print ('Token obtained is: ' + token)
        else:
	        print ('ERROR ' + str(response.status_code) + 'while we trying to requests a token')
        return token	

    def send_metric (self, metric_name, dimensions, value, value_meta):
        url = self.monclient_url + '/v2.0/metrics' 
        payload = {	'name': metric_name, 'dimensions': dimensions,'timestamp': time.time() * 1000, 'value': value, 'value_meta': value_meta}
        msg = json.dumps(payload)
        head = { 'Content-type':'application/json', 'X-Auth-Token':self.token }
        #print('Sending metric: ' + msg+ '....')
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.post( url, headers=head, data=msg )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if (ok):        
            if (response.status_code == 204):
            	print('Successfully created metric ' + metric_name)
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                response = self.send_metric (metric_name, dimensions, value, value_meta)
            else:
                print('ERROR ' + str(response.status_code) + ' when we trying to create metric '+ metric_name)    
        else:
            print('ERROR: Cannot connect to ' + url + '. Metric not sent.')
        return response

    def send_metric_json (self, metric):
        if (not self.checkMetric(metric)):
            print('ERROR: JSON metric is not correct')
            return {}
        url = self.monclient_url + '/v2.0/metrics'
        metric['timestamp'] = time.time() * 1000 
        msg = json.dumps(metric)
        head = { 'Content-type':'application/json', 'X-Auth-Token':self.token }        
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.post( url, headers=head, data=msg )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if (ok):   
            if (response.status_code == 204):
            	print('Successfully created metric ' + metric['name'])
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                response = self.send_metric_json(metric)
            else:
                print('ERROR ' + str(response.status_code) + ' when we trying to create metric '+ metric['name'])
        else:
            print('ERROR: Cannot connect to ' + url + '. Metric not sent.')        
        return response

    # Return JSON
    def send_alarm (self, alarm_name, description, expression, severity, ok_actions, alarm_actions, undetermined_actions, match_by):
        url = self.monclient_url + '/v2.0/alarm-definitions'
        ok = True
        payload = {	'name': alarm_name, 'description': description, 'expression': expression, 'ok_actions':ok_actions, 'match_by': match_by , 'alarm_actions': alarm_actions, 'undetermined_actions': undetermined_actions }
        for sev in severity.split('|'):
	        if not sev in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
		        ok = False
        if ok:
	        payload['severity'] = severity
        msg = json.dumps(payload)
        #print('Creating alarm: ' + msg+ '....')
        head = { 'Content-Type':'application/json', 'X-Auth-Token': self.token }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.post( url, headers=head, data=msg )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:               
            if (response.status_code == 201):
            	res=json.loads(response.text)
            	print('Successfully created alarm ' + alarm_name + ' with id = ' + res["id"])
            	return res
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.send_alarm (alarm_name, description, expression, severity, ok_actions, alarm_actions, undetermined_actions, match_by)
            else: 
            	 print('ERROR ' + str(response.status_code) + ' when we trying to create alarm '+ alarm_name)
        else: 
            print('ERROR: Cannot connect to ' + url + '. Alarm not sent.') 
        return {} 

    def send_alarm_json (self, alarm):
        if (not self.checkAlarm(alarm)):
            print('ERROR: JSON alarm is not correct')
            return {}

        url = self.monclient_url + '/v2.0/alarm-definitions'
        # Check severity
        severity = ''
        ok=True
        for sev in alarm['severity'].split('|'):	        
	        if sev in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
		        if (len(severity)>=1):
	        		severity += '|'
	        	severity += sev
	        else:
	        	ok=False
        if (ok):
	        alarm['severity'] = severity
        else:
	        del alarm['severity']

        msg = json.dumps(alarm)
        #print('Creating alarm: ' + msg + '....')
        head = { 'Content-Type':'application/json', 'X-Auth-Token': self.token , 'Accept' :'application/json' }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.post( url, headers=head, data=msg )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:        
            if (response.status_code == 201):
            	res=json.loads(response.text)
            	print('Successfully created alarm ' + alarm['name'] + ' with id = ' + res["id"])
            	return res
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.send_alarm_json(alarm)
            else: 
            	 print('ERROR ' + str(response.status_code) + ' when we trying to create alarm '+ alarm['name'])
        else: 
            print('ERROR: Cannot connect to ' + url + '. Alarm not sent.') 
        return {} 

    def get_notification_list (self):
        url = self.monclient_url + '/v2.0/notification-methods'
        head = { 'Content-Type':'application/json', 'X-Auth-Token': self.token }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.get( url, headers = head)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                info = json.loads(str(response.text))
                return info
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.get_notification_list()
            else:        
                print('ERROR '+ str(response.status_code) + ' : when we trying to obtain notification methods') 
        else: 
            print('ERROR: Cannot connect to ' + url ) 
        return {}        

    def get_notification (self, name):
        url = self.monclient_url + '/v2.0/notification-methods/' + name
        head = { 'Content-Type':'application/json', 'X-Auth-Token': self.token }
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.get( url, headers = head)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                info = json.loads(str(response.text))
                return info
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.get_notification(name)
            else:        
                print('ERROR '+ str(response.status_code) + ' : when we trying to obtain information of ' + name + ' notification method') 
        else: 
            print('ERROR: Cannot connect to ' + url ) 
        return {}     

    def create_notification(self, notification ):
        url = self.monclient_url + '/v2.0/notification-methods'
        head = { 'Content-Type':'application/json', 'Accept':'application/json', 'X-Auth-Token': self.token }
        msg = json.dumps(notification)
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.post( url, headers=head, data=msg )
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 201):
                info = json.loads(str(response.text))
                print('Successfully created notification ' + notification['name'] + ' with id = ' + info['id'])
                return info
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.create_notification(notification)
            else:          
                print('ERROR '+ str(response.status_code) + ' : when we trying to create Notification '+ notification['name']) 
        else: 
            print('ERROR: Cannot connect to ' + url ) 
        return {}  

    def get_metric_statistics (self, parameters): 
        url = self.monclient_url + '/v2.0/metrics/statistics'
        head = { 'Content-Type':'application/json', 'Accept':'application/json', 'X-Auth-Token': self.token }
        query = '?'
        for key in parameters.keys():
            query += key + '=' + str(parameters[key])  + '&'
        url += query[:-1]# remove last &
        response = None
        retries = 0
        ok = False
        while ( (self.max_retries>retries) and (not ok) ):
            retries += 1
            try: 
                response = requests.get( url, headers = head)
                ok=True
            except requests.exceptions.ConnectionError:
                print (url + ': Connection refused, waiting 5 seconds...') 
                time.sleep(5)
        if ok:
            if (response.status_code == 200):
                info = json.loads(str(response.text))
                return info
            elif (response.status_code == 401): #Auth
                self.token = self.request_token()
                return self.get_metric_statistics(parameters)
            else:        
                print('ERROR '+ str(response.status_code) + ' : when we trying to get statistics of metric ' + parameters['name']) 
        else:
            print('ERROR: Cannot connect to ' + url ) 
        return {} 
