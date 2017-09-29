#!/usr/bin/env python

from requests import *
from ManagerMarathon import *
from ManagerChronos import *
from datetime import *
import sys, getopt, uuid, time


def help():
	print ('USAGE: launcher.py\n\t-i <api_rest_ip>: url for REST API. Example: http://10.0.0.2:30000\n\t-j <job-file>: job definition for the framework in json\n\t-m <credentials-marathon>: json with credentials-marathon\n\t-c <credentials-chronos>: json with credentials-chronos\n\t')

def get_arguments():
	job_file_name = ''
	credentials_chronos_name = ''
	credentials_marathon_name = ''
	credentials_framework_name = ''
	credentials_framework = ''
	api_rest_ip = ''
	framework_name = ''
	framework = None
	jobname = ''
	iterations = -1
	job = None

	try:
		opts, args = getopt.getopt( sys.argv[1:],'hm:j:c:i:',['credentials-marathon=','job-file=',  'credentials-chronos=','rest-ip='])
		
	except getopt.GetoptError:
		help()
		sys.exit(2)

	if len(opts) == 0:
		help()
	for opt, arg in opts:
		if opt == '-h':
			help()
			sys.exit()
		elif opt in ("-j", "--job-file"):
			job_file_name = arg     	
		elif opt in ("-c", "--credentials-chronos"):
			framework_name='chronos'
			credentials_chronos_name = arg
			credentials_framework_name = arg
		elif opt in ("-m", "--credentials-marathon"):
			credentials_marathon_name = arg
			credentials_framework_name = arg
			framework_name='marathon'
		elif opt in ("-i", "--rest-ip"):
			api_rest_ip = arg
		
	if ( job_file_name == '' ) or (framework_name == '') or (api_rest_ip == '' ): 
		print ('ERROR: At least the program needs: <rest-ip>, <job-file> and <credentials-marathon> / <credentials-chronos>') 
		sys.exit(1)

	if (credentials_chronos_name != '') and (credentials_marathon_name != ''):
		print ('ERROR: You must select ONE framework_name to deploy') 
		sys.exit(1)

	# Read JSONs of Monasca and JOB
	job_file = open( job_file_name , 'r')
	
	try: 
		job = json.loads( job_file.read() )
	except (ValueError):
		print('ERROR: Invalid JSON in job file')	
		sys.exit(1)

	if not 'container' in job:
		print('ERROR: You must pass containerized job')
		sys.exit(1)

	credentials_framework_file = open( credentials_framework_name, 'r')
	try: 
		credentials_framework = json.loads( credentials_framework_file.read() )
	except (ValueError):
		print('ERROR: Invalid JSON in credentials-framework-file file')
		sys.exit(1)
		
	if (framework_name == 'chronos'):
		framework = ManagerChronos (credentials_framework['url'], credentials_framework['user'], credentials_framework['password'])
		jobname = job['name'] 

	elif (framework_name == 'marathon'):
		jobname = job['id'][1:]	
		framework = ManagerMarathon(credentials_framework['url'], credentials_framework['user'], credentials_framework['password'])

	return framework, framework_name, job, str(jobname), credentials_framework_name, api_rest_ip

def get_payload(framework_name, jobname, job_duration, deadline, desv_deadline, myUUID):	
	payload = {
			'framework': framework_name,
		   	'name': jobname,
		   	'job_duration': job_duration,
		   	'deadline': deadline,
		   	'desv_deadline': desv_deadline,
		   	'uuid': myUUID
	}	
	if (framework_name == 'chronos'):
		payload['iterations'] = int( job['schedule'].split('/')[0][1:] )
	
	return payload

def init_webhook( url_webhook, payload ):
	head = { 'Content-type':'application/json'}
	url = url_webhook+'/initTask'
	msg = json.dumps(payload)
	response = requests.post( url, headers=head, data=msg )

def modify_job(api_rest_ip, framework_name, jobname, myUUID, executor_path, checkpoint_dir, marathon_init_url_webhook, marathon_end_url_webhook, taskKillGracePeriodSeconds) :
	if (framework_name == 'chronos'):
		updateCommand_1 = "startedAt=$(date +%s); "
		updateCommand_2 = "; /usr/bin/curl -H 'Content-type: application/json' -X POST " + api_rest_ip +"/updateTask -d '{\"name\": \"" + jobname + "\", \"finished_at\": \"'$(date +%s)'\", \"started_at\": \"'$(echo $startedAt)'\", \"hostname\": \"'$(hostname)'\", \"uuid\": \"" + myUUID + "\"}'"
		job['command'] = updateCommand_1 + job['command'] + updateCommand_2
		job['schedule'] = 'R//' + job['schedule'].split('/')[2] 
		#print(job['schedule'])

	elif (framework_name == 'marathon'):

		# Check instances
		if (job['instances'] != 1): 
			print("Invalid number of instances ( job['instances'] = "+str(job['instances'])+"), forcing to 1 and continue...")
			job['instances'] = 1

		# Set command to execute
		cmd = job['cmd']
		job['cmd'] = executor_path + ' $MY_UUID $MY_CHECKPOINT_DIR $MY_DOCKER_IMAGE $MY_START_URL_WEBHOOK $MY_END_URL_WEBHOOK \"$MY_DOCKER_OPTIONS\" \"'+ cmd + '\"'
		
		# Environmental variables
		if not ('env' in job):
			job['env'] = {}
		job['env']['MY_START_URL_WEBHOOK'] = api_rest_ip + marathon_init_url_webhook
		job['env']['MY_END_URL_WEBHOOK'] = api_rest_ip + marathon_end_url_webhook
		job['env']['MY_UUID'] = myUUID
		job['env']['MY_CHECKPOINT_DIR'] = checkpoint_dir
		job['env']['MY_DOCKER_IMAGE'] = job['container']['docker']['image']
		job['env']['MY_DOCKER_OPTIONS'] = ''
		
		
		# Docker volumes
		if 'volumes' in job['container']:
			for volume in job['container']['volumes']:
				job['env']['MY_DOCKER_OPTIONS'] += '-v '+ volume['hostPath'] + ':' + volume['containerPath'] + ':' + volume['mode'].lower() + ' '
	        '''	
		# Docker network
		if 'network' in job['container']['docker']:
			networkType = job['container']['docker']['network'].lower()
			if (networkType in ['bridge','host'] ):
				job['env']['MY_DOCKER_OPTIONS'] += '--net=' + networkType + ' '
			else:
				print ("ERROR: job['container']['docker']['network'] is not BRIDGE or HOST")	
				sys.exit(1)

		# Docker Port Mappings
		if 'portMappings' in job['container']['docker']:
			for item in job['container']['docker']['portMappings']:
				if not (('containerPort' in item) and ('hostPort' in item)):
					print ("ERROR: job['container']['docker']['portMappings'] must contain containerPort and hostPort")
					sys.exit(1)
				if ((item['hostPort'] == 0 ) or (item['containerPort'] == 0)):
					print("ERROR: hostPort and containerPort must not be 0")
					sys.exit(1)
				job['env']['MY_DOCKER_OPTIONS'] += '-p ' + item['hostPort'] + ':' + item['containerPort']

				if 'protocol' in item:
					if item['protocol'].lower() in ['tcp','udp']:
						job['env']['MY_DOCKER_OPTIONS'] += '/' + item['protocol'].lower()

				job['env']['MY_DOCKER_OPTIONS'] += ' '

		# Docker parameters
		if 'parameters' in job['container']['docker']:
			for item in job['container']['docker']['parameters']:
				job['env']['MY_DOCKER_OPTIONS'] += item['key'] + ' '+ item['value']+ ' '
				
		# Docker privileged
		if 'privileged' in job['container']['docker']:
			if bool(job['container']['docker']['privileged']):
				job['env']['MY_DOCKER_OPTIONS'] += '--privileged'	
                '''  
		# Remove Containerized Job
		del job['container']

		# Add grace period for checkpointing
		job['taskKillGracePeriodSeconds'] = taskKillGracePeriodSeconds

	del job['qos']
	return job

def get_deadline(framework_name, job, start_job):
	if (framework_name == 'chronos'):
		deadline = job['qos']['deadline'] + start_job # seconds epoch
	elif (framework_name == 'marathon'):
		deadline = job['qos']['deadline']
	return deadline

def generateUUID():
	return str(uuid.uuid4().hex)

if __name__ == '__main__':

	# Configuration options
	executor_path = '/home/users/shared/serlophug/checkpointing/Executor.sh'
	checkpoint_dir = '/home/users/shared/serlophug/checkpointing'
	taskKillGracePeriodSeconds = 120

	# REST API
	marathon_init_url_webhook = '/initMarathonApp'
	marathon_end_url_webhook = '/endMarathonApp'
	
	#deadline_timestamp = int(deadline.strftime("%s"))
	framework, framework_name, job, jobname, credentials_framework_name, api_rest_ip = get_arguments()

	start_job = time.time() # datetime.utcnow()
	deadline = get_deadline(framework_name, job, start_job)
	job_duration = job['qos']['duration'] # seconds
	desv_deadline = job['qos']['desv_deadline'] # %/100 (e.g 5% --> desv_deadline=0.05 )
	myUUID = generateUUID()

	payload = get_payload(framework_name, jobname, job_duration, deadline, desv_deadline, myUUID)
	job = modify_job(api_rest_ip, framework_name, jobname, myUUID, executor_path, checkpoint_dir, marathon_init_url_webhook, marathon_end_url_webhook, taskKillGracePeriodSeconds)
	
	if ( framework.sendJob(job) ):
		print('Launch completed with UUID: '+ myUUID)
		init_webhook(api_rest_ip, payload)
	else:
		print('ERROR: Launch not completed')
