#!/usr/bin/env python

from ManagerMonasca import *
from ManagerMarathon import *
from ManagerChronos import *
from Metrics import *
from InfiniteTimer import *
from threading import Lock, Timer
from flask import Flask, url_for, request
import json
import logging
import time
import datetime
import getopt
import sys
import os



# Config parameters
sleeping_time = 0 # CHRONOS: Between startJob calls
logDirectory = '/home/users/bigsea/serlophug/log'
deployment_time = 45
ticksPerSecond = 100.0
monitoring_period = 120
# Elasticity parameters
cpu_max_slave = 2.0
cpu_min_slave = 0.1
cpu_increment = 0.4
cpu_decrement = 0.4

mutex = Lock()
app = Flask(__name__)
allinfo = {'chronos': {}, 'marathon': {}}

def help():
    print('USAGE: supervisor.py\n\t-i <api_rest_ip>: ip for REST API. Optional\n\t-p <api_rest_port>: port for REST API. Optional\n\t-m <credentials-marathon>: json with credentials-marathon\n\t-o <credentials-openstack>: json with credentials for keystone and monasca\n\t-c <credentials-chronos>: json with credentials-chronos\n\t')
            
def init_log(logDirectory):
    filename = logDirectory + '/' +datetime.datetime.utcnow().strftime("%Y%m%d") + '.log'
    if not os.path.isfile(filename): 
        file(filename, 'w').close()
    global logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler_info = logging.FileHandler(filename)
    handler_info.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')# create a logging format
    handler_info.setFormatter(formatter)
    logger.addHandler(handler_info) # add the handlers to the logger

def get_arguments():
    global monasca, chronos, marathon, api_rest_ip, api_rest_port
    credentials_openstack_name = ''
    credentials_chronos_name = ''
    credentials_marathon_name = ''
    api_rest_ip = '0.0.0.0'
    api_rest_port = '30000'
    try:
        opts, args = getopt.getopt( sys.argv[1:],'ho:m:c:i:p:',['credentials-openstack=', 'credentials-marathon=', 'credentials-chronos=', 'rest-ip=','rest-port='])
    except getopt.GetoptError:
        help()
        sys.exit(2)
    if len(opts) == 0:
        help()
    for opt, arg in opts:
        if opt == '-h':
            help()
            sys.exit()
        elif opt in ("-o", "--credentials-openstack"):
            credentials_openstack_name = arg
        elif opt in ("-c", "--credentials-chronos"):
            credentials_chronos_name = arg
        elif opt in ("-m", "--credentials-marathon"):
            credentials_marathon_name = arg
        elif opt in ("-i", "--rest-ip"):
            api_rest_ip = arg
        elif opt in ("-p", "--rest-port"):
            api_rest_port = int(arg)

    if ( credentials_marathon_name == '' ) or (credentials_chronos_name == '') or (credentials_openstack_name == '') :
        print ('ERROR: At least the program needs 3 arguments: <credentials-openstack>, <credentials-marathon> and <credentials-chronos>')
        sys.exit(1)

    credentials_openstack_file = open( credentials_openstack_name, 'r')
    credentials_chronos_file = open( credentials_chronos_name, 'r')
    credentials_marathon_file = open( credentials_marathon_name, 'r')
    try:
        credentials_openstack = json.loads( credentials_openstack_file.read() )
        credentials_chronos = json.loads( credentials_chronos_file.read() )
        credentials_marathon = json.loads( credentials_marathon_file.read() )
    except (ValueError):
        print('ERROR: Invalid JSONs in credential files')
        sys.exit(1)

    monasca = ManagerMonasca(credentials_openstack['keystone_url'], credentials_openstack['username'], credentials_openstack['password'], credentials_openstack['project_name'], credentials_openstack['monocasca_client_url'])
    chronos = ManagerChronos (credentials_chronos['url'], credentials_chronos['user'], credentials_chronos['password'])
    marathon = ManagerMarathon(credentials_marathon['url'], credentials_marathon['user'], credentials_marathon['password'])

def init_task ( data ):
    mutex.acquire(1)
    allinfo [ data['framework'] ] [ data['uuid'] ] = {
        'name': data['name'],
        'framework' : data['framework'],
        'job_duration': data['job_duration'],
        'desv_deadline': data['desv_deadline'],
        'deadline': data['deadline'],
        'current_cpu': 0.0,
        'last_job_duration':0,
        'allexecutions_duration': [],
        'uuid': data['uuid']
    }
    current_time = int(time.time()) 
    if (data['framework'] == 'chronos'):         
        
        allinfo [ data['framework'] ][ data['uuid'] ][ 'iterations'] = data['iterations']
        allinfo [ data['framework'] ][ data['uuid'] ][ 'current' ] =  current_time
        allinfo [ data['framework'] ][ data['uuid'] ]['allexecutions_hostname'] = []

        timeBeforeDeadline = int(data['deadline'])  - int(time.time())
        #allinfo [ data['framework'] ][ data['uuid'] ][ 'deadline_inf'] = data['deadline'] - data['desv_deadline']*timeBeforeDeadline
        allinfo [ data['framework'] ][ data['uuid'] ][ 'deadline_inf'] = current_time + data['desv_deadline']*timeBeforeDeadline
        allinfo [ data['framework'] ][ data['uuid'] ][ 'deadline_sup'] = data['deadline'] - 0.05*timeBeforeDeadline
        
        chronos.startJob(data['name'])
        send_metrics (  [ get_metric_remaining_iterations( data['uuid'], allinfo [ data['framework'] ]) ] )

    elif (data['framework'] == 'marathon'):
        allinfo [ data['framework'] ][ data['uuid'] ][ 'init_time' ] = [] 
        allinfo [ data['framework'] ][ data['uuid'] ]['current_cputime_accumulated_all'] = 0
        allinfo [ data['framework'] ][ data['uuid'] ]['current_cputime_accumulated'] = 0
        allinfo [ data['framework'] ][ data['uuid'] ]['desired_cputime_accumulated'] = 0
        allinfo [ data['framework'] ][ data['uuid'] ]['marathon_ratio_progress'] = 0
        allinfo [ data['framework'] ][ data['uuid'] ]['isRunning'] = False


    # allinfo [ data['framework'] ] [ data['name'] ][ ] = 
    logger.info('NEW TASK: ' + data['name'] + ' with UUID: '+ data['uuid'])
    logger.info('INFO: ' + json.dumps(allinfo))

    mutex.release()   

def send_metrics ( metrics ):
    for item in metrics:
        monasca.send_metric_json( item )
   
def get_prediction_chronos (uuid, info):
    jobname = info[ uuid ]['name']
    current = info[ uuid ]['current']
    remaining_iterations = info[ uuid ][ 'iterations' ]
    job_duration = info[ uuid ]['job_duration']
    deadline_sup = info[ uuid ]['deadline_sup']
    deadline_inf = info[ uuid ]['deadline_inf']

    prediction = current + ((job_duration +  sleeping_time + deployment_time ) * remaining_iterations)
    logger.info('Chronos - Prediction of ' +  jobname +' is '+ str(prediction) + ' and Deadline SUP is '+ str(deadline_sup) + ' --> ' + str(prediction - deadline_sup))
    logger.info('Chronos - Prediction of ' +  jobname +' is '+ str(prediction) + ' and Deadline INF is '+ str(deadline_inf) + ' --> ' + str(deadline_inf - prediction ))
    return prediction

def update_task_chronos( data ): 
    logger.info( 'Chronos - UpdateChronosJSON: ' + json.dumps(data) )
    # data:
    uuid = data['uuid']
    jobname = data['name']
    #framework_name =  #data['framework'] 
    finished_at = int( data['finished_at'] )
    started_at = int( data['started_at'] ) 
    hostname = str(data['hostname'])
    mutex.acquire()

    info = allinfo[ 'chronos' ] 
    if (uuid in info): # TASK RECOGNIZED
        job_json = chronos.getInfo( jobname )
        # Update values
        info[ uuid ]['current'] = finished_at
        info[ uuid ]['last_job_duration'] = finished_at - started_at 
        info[ uuid ]['allexecutions_duration'].append(info[ uuid ]['last_job_duration'])
        info[ uuid ]['allexecutions_hostname'].append( hostname )
        info[ uuid ]['current_cpu'] = job_json['cpus']

        # Update remaining iterations
        info[ uuid ][ 'iterations' ] -= 1         
        
        #logger.info('Chronos - CHECK JOB: ' + jobname +' -> schedule: ' + str(job_json['schedule']) + ' -- remaining_iterations: ' + str( info[ uuid ][ 'iterations' ] ))
        logger.info('Chronos - CHECK JOB: ' + jobname +' --> remaining_iterations: ' + str( info[ uuid ][ 'iterations' ] ))
        
        # Calculate prediction
        info[ uuid ][ 'prediction' ] = get_prediction_chronos( uuid, info )

        # Sends metrics to Monasca
        metrics_desired = [
            get_metric_prediction_vs_deadline(uuid, info),
            get_metric_remaining_iterations(uuid, info),
            get_metric_current_cpu (uuid, info),
            get_metric_job_duration (uuid, info)
        ]           
            
        send_metrics ( metrics_desired )       
        
        # JOB FINALIZED?
        if ( info[ uuid ]['iterations']  <= 0): # All iterations done
            # Chronos has more iterations scheduled?
            #job_json['schedule'] = 'R0//PT1M'
            #chronos.sendJob(job_json)   
            chronos.deleteJob(jobname)
            ontime = False
            remaining_time = info[ uuid ]['current'] - info[ uuid ]['deadline'] 
    	    if ( remaining_time <= 0):
                ontime = True
            logger.info('Chronos - JOB COMPLETED: ' + jobname+ ' with UUID = ' + uuid +'. Ended in time? ' + str(ontime) + ' --> '+ str(remaining_time) )
            # Update dictionary
            del info[ uuid ]                            
        else: 
            # Elasticity?
            state = check_state_chronos ( info[ uuid ][ 'prediction' ] , info[ uuid ][ 'deadline_sup' ] , info[ uuid ][ 'deadline_inf' ] ) 
            logger.info( 'Chronos - STATE of '+ jobname +' is ' + state)
            needsSend = False

            if ( state == 'OVER_PERFORMANT'):
                needsSend, job_json = alarm_state_inf( info [ uuid ] , job_json)                 
            elif ( state == 'UNDER_PERFORMANT'):                
                needsSend, job_json = alarm_state_sup( info [ uuid ] , job_json)    
            
            if (needsSend):
                chronos.sendJob(job_json)  
                info[ uuid ]['current_cpu'] = job_json['cpus']

            # Start again
            logger.info('Chronos - Sleeping job'+ jobname + ': ' + str(sleeping_time) +' seconds...')
            time.sleep( sleeping_time )
            chronos.startJob( jobname  )
            logger.info('Chronos - JOB STARTED: ' + jobname)

    else: # TASK NOT RECOGNIZED
        logger.info('Crhonos - ERROR: TASK'+ jobname +' with UUID = ' + uuid +' NOT RECOGNIZED')       
    mutex.release()
        
def check_state_chronos( prediction, deadline_sup, deadline_inf):
    if ( prediction > deadline_sup ):
        return 'UNDER_PERFORMANT'
    elif ( prediction < deadline_inf ):
        return 'OVER_PERFORMANT'
    else:
        return 'ON_PLAN'

def alarm_state_inf (data,job): 
    needsSend = True 
    if (data['framework'] == 'chronos'):
        if ( job['cpus'] - cpu_decrement >= cpu_min_slave):
            job['cpus'] -= cpu_decrement
            logger.info('Chronos - JOB DECREMENT : '+ data['name'] +'. New CPU value: ' + str(job['cpus']))
        else:
            if (job['cpus'] != cpu_min_slave):
                job['cpus'] = cpu_min_slave
                logger.info('Chronos - JOB MAX DECREMENT: '+ data['name'] +'. New CPU value: ' + str(job['cpus']) )
            else:
                needsSend = False
                logger.info('Chronos - JOB MAX DECREMENT: '+ data['name'] +'. CPU value: ' + str(job['cpus']) )              
    elif (data['framework'] == 'marathon'):
        if ( job['cpus'] - cpu_decrement >= cpu_min_slave):
            job['cpus'] -= cpu_decrement
            logger.info('Marathon - JOB DECREMENT : '+ data['name'] +'. New CPU value: ' + str(job['cpus']))
        else:
            if (job['cpus'] != cpu_min_slave):
                job['cpus'] = cpu_min_slave
                logger.info('Marathon - JOB MAX DECREMENT: '+ data['name'] +'. New CPU value: ' + str(job['cpus']) ) 
            else:
                needsSend = False
                logger.info('Marathon - JOB MAX DECREMENT: '+ data['name'] +'. CPU value: ' + str(job['cpus']) ) 
    return needsSend, job

def alarm_state_sup ( data, job ) : 
    needsSend = True
    if (data['framework'] == 'chronos'):                 
        if ( job['cpus'] + cpu_increment <= cpu_max_slave):
            job['cpus'] += cpu_increment         
            logger.info( 'Chronos - JOB INCREMENT : '+ data['name'] +'. New CPU value: ' + str(job['cpus']) )
        else:
            if (job['cpus'] != cpu_max_slave):   
                job['cpus'] = cpu_max_slave 
                logger.info('Chronos - JOB MAX INCREMENT: '+ data['name'] +'. New CPU value: ' + str(job['cpus']) )  
            else:
                needsSend = False
                logger.info('Chronos - JOB MAX INCREMENT: '+ data['name'] +'. CPU value: ' + str(job['cpus']) )   
    elif (data['framework'] == 'marathon'):
        if ( job['cpus'] + cpu_increment <= cpu_max_slave):
            job['cpus'] += cpu_increment
            logger.info( 'Marathon - JOB INCREMENT : '+ data['name'] +'. New CPU value: ' + str(job['cpus']) )
        else:
            if (job['cpus'] != cpu_max_slave):   
                job['cpus'] = cpu_max_slave 
                logger.info( 'Marathon - JOB MAX INCREMENT : '+ data['name'] +'. New CPU value: ' + str(job['cpus']) )
            else:
                needsSend = False
                logger.info('Marathon - JOB MAX INCREMENT: '+ data['name'] +'. CPU value: ' + str(job['cpus']) ) 
    return needsSend, job

def init_marathon_app(data):
    uuid = data['uuid']
    mutex.acquire()
    if (uuid in allinfo[ 'marathon' ]):
        allinfo[ 'marathon' ][ uuid ][ 'init_time' ] = [ float(data['started_at']) ]
        allinfo [ 'marathon' ][ uuid ]['current_cputime_accumulated'] = 0
        allinfo [ 'marathon' ][ uuid ]['desired_cputime_accumulated'] = 0
        allinfo [ 'marathon' ][ uuid ]['current_cputime_accumulated_all'] = 0
        allinfo [ 'marathon' ][ uuid ]['marathon_ratio_progress'] = 1.0
        allinfo[ 'marathon' ][ uuid ]['isRunning'] = True
        metrics_desired = [
            get_metric_current_cputime_accumulated (uuid, allinfo[ 'marathon' ]),
            get_metric_desired_cputime_accumulated (uuid, allinfo[ 'marathon' ]),
            get_metric_marathon_ratio_progress( uuid, allinfo[ 'marathon' ]),
            get_metric_marathon_cputime_current_vs_desired( uuid, allinfo[ 'marathon' ])
        ]
        send_metrics( metrics_desired)
        jobname = allinfo[ 'marathon' ][ uuid ][ 'name' ]
        logger.info('Marathon - JOB STARTED: '+ jobname + ' with UUID = ' + uuid )
    mutex.release()

def end_marathon_app(data):
    ontime = False
    uuid = data['uuid']
    finished_at = data['finished_at']
    mutex.acquire()
    if (uuid in allinfo[ 'marathon' ]):
        started_at = allinfo[ 'marathon' ][ uuid ][ 'init_time' ][0]
        current_time = time.time()
        
        # Update values for send last metric
        allinfo[ 'marathon' ][ uuid ][ 'last_job_duration' ] = float(finished_at) - float(started_at) 
        allinfo[ 'marathon' ][ uuid ][ 'allexecutions_duration' ].append( allinfo[ 'marathon' ][ uuid ][ 'last_job_duration' ])

        current_cpu_host = get_cpu_from_monasca(uuid, allinfo[ 'marathon' ], current_time) #
        current_cpu = allinfo[ 'marathon' ][ uuid ]['current_cputime_accumulated_all'] + current_cpu_host   
        current_cpu_percent = current_cpu / float( allinfo[ 'marathon' ][uuid]['job_duration'] ) 
        desired_cpu_percent = get_desired_cpu_percent (uuid, allinfo[ 'marathon' ], current_time)

        allinfo[ 'marathon' ][uuid]['current_cputime_accumulated'] = current_cpu
        allinfo[ 'marathon' ][uuid]['desired_cputime_accumulated'] = desired_cpu_percent * float( allinfo[ 'marathon' ][uuid]['job_duration'] )
        allinfo[ 'marathon' ][uuid]['marathon_ratio_progress'] = current_cpu_percent / desired_cpu_percent 
        

        print( 'current_cpu_host: ' + str(current_cpu_host) +', current_cpu: ' + str(current_cpu) +', current_cputime_accumulated: ' + str(allinfo[ 'marathon' ][uuid]['desired_cputime_accumulated']) +', desired_cputime_accumulated: ' + str( allinfo[ 'marathon' ][uuid]['desired_cputime_accumulated'] ))
        # Send metrics
        metrics_desired = [
            get_metric_current_cpu (uuid, allinfo[ 'marathon' ]),
            get_metric_job_duration (uuid, allinfo[ 'marathon' ]),
            get_metric_current_cputime_accumulated (uuid, allinfo[ 'marathon' ]),
            get_metric_desired_cputime_accumulated (uuid, allinfo[ 'marathon' ]),
            get_metric_marathon_ratio_progress( uuid, allinfo[ 'marathon' ]),
            get_metric_marathon_cputime_current_vs_desired( uuid, allinfo[ 'marathon' ])
        ]
        send_metrics( metrics_desired)
 
        jobname = allinfo[ 'marathon' ][ uuid ][ 'name' ]
        remaining_time = allinfo[ 'marathon' ][ uuid ][ 'last_job_duration' ] - allinfo[ 'marathon' ][ uuid ]['deadline']  
        if ( remaining_time <= 0):
            ontime = True
        logger.info('Marathon - JOB COMPLETED: '+ jobname + ' with UUID = ' + uuid +'. Ended in time? ' + str(ontime) + ' --> Rem Time: ' + str(remaining_time) + ', CPU Time: ' + str(current_cpu) ) 
        allinfo[ 'marathon' ][ uuid ]['isRunning'] = False
    mutex.release()  
 
def get_desired_cpu_percent (uuid, info, current_time):
    init_time = float(info[uuid]['init_time'][0])
    if (current_time >= (init_time + float(info[uuid]['deadline'])) ):
        print('\nget_desired_cpu_percent of '+ info[uuid]['name'] +' --> 1.0\n')
        return 1.0
    percent_cpu_elapsed = (current_time - init_time) / float(info[uuid]['deadline'])
    print('\nget_desired_cpu_percent of '+ info[uuid]['name'] +' --> current_time = '+ str(current_time) + ', init_time = '+ str(init_time) +', info[uuid]["deadline"] = '+ str(info[uuid]['deadline']) + ', percent_cpu_elapsed = ' + str(percent_cpu_elapsed) +'\n')
    return float(percent_cpu_elapsed)

def get_cpu_from_monasca( uuid, info, current_time, retries=0 ):
    if (retries <= 10):
        #print ("info[uuid]['init_time']: " + str(info[uuid]['init_time']))
        init_time_epoch = info[uuid]['init_time'][-1] 
        period_seconds = int(current_time - init_time_epoch )
        init_time_iso = str( datetime.datetime.utcfromtimestamp( init_time_epoch ).isoformat() )
        current_time_iso = str( datetime.datetime.utcfromtimestamp( current_time ).isoformat() )

        dimensions = 'name:' + uuid
        query_parameters = {
            'name': 'container.cpu.user_time',
            'statistics': 'max',
            'dimensions': dimensions,
            'start_time': init_time_iso,
            'end_time': current_time_iso,
            'period': period_seconds,
            'merge_metrics': True
        }
        print ('query_parameters: ' + json.dumps(query_parameters) + '\n')

        query_result_user_time = monasca.get_metric_statistics( query_parameters )
        length = len(query_result_user_time['elements'])
        if (length==0):
            logger.info('Marathon - METRIC container.cpu.user_time not available for '+ str(info[uuid]['name']) +' with UUID=' + uuid +', sleep 5 seconds...')
            time.sleep(5)
            return get_cpu_from_monasca( uuid, info, current_time, retries+1 )
       
        print('query_result_user_time: ' + json.dumps(query_result_user_time))

        user_time = 0.0
        for element in query_result_user_time['elements'][0]['statistics']:
            if (user_time < float(element[1])):
                user_time = float(element[1])

        user_time = user_time / ticksPerSecond
        query_parameters['name'] = 'container.cpu.system_time'
        query_result_system_time = monasca.get_metric_statistics( query_parameters )
        
        print('query_result_system_time: ' + json.dumps(query_result_system_time))
        system_time = 0.0
        for element in query_result_system_time['elements'][0]['statistics']:
            if (system_time < float(element[1])):
                system_time = float(element[1])

        system_time = system_time / ticksPerSecond   
        print('user_time: ' + str(user_time) +'system_time: ' + str(system_time))
        return  float(user_time) + float(system_time)
    else: 
        logger.info('Marathon - METRIC container.cpu.user_time not available for '+ str(info[uuid]['name']) +' with UUID=' + uuid +', forcing current_cputime = 0')
        return float(0)

def check_state_marathon (current_cputime, desired_cputime, desv_deadline):
    rate = current_cputime / desired_cputime
    #if (rate < (1.0 - desv_deadline)  ):
    if (rate < 0.95):
            return 'UNDER_PERFORMANT'
    #elif (rate > (1.0 + desv_deadline)  ):
    elif (rate > (1.0 + desv_deadline)):
        return 'OVER_PERFORMANT'
    else:
        return 'ON_PLAN'

def main_marathon():
    global mutex, allinfo, monasca, marathon, logger, monitoring_period

    # Get my info
    mutex.acquire()

    info = allinfo['marathon']
    keys = info.keys()
    for uuid in keys:
        jobname = info[uuid]['name']
        job_json = marathon.getInfo( jobname )

        if info[ uuid ]['isRunning'] and job_json != {}:            
            
            current_time = float(time.time())
            print('current_time: '+ str( datetime.datetime.utcfromtimestamp( current_time ).isoformat() ))
            # Compute DESIRED accumulated cpu
            desired_cpu_percent = get_desired_cpu_percent (uuid, info, current_time)
            # Get CURRENT accumulated cpu FROM Monasca
            current_cpu_host = get_cpu_from_monasca(uuid, info, current_time) #
            current_cpu = info[ uuid ]['current_cputime_accumulated_all'] + current_cpu_host
            print('current_cpu_host: ' + str(current_cpu_host))
            print('current_cputime_accumulated_all: ' + str(info[ uuid ]['current_cputime_accumulated_all']))
            print('current_cpu: ' + str(current_cpu))
            current_cpu_percent = current_cpu / float( info[uuid]['job_duration'] ) 

            # Update values
            info[uuid]['current_cpu'] = job_json['cpus']
            info[uuid]['current_cputime_accumulated'] = current_cpu
            info[uuid]['desired_cputime_accumulated'] = desired_cpu_percent * float( info[uuid]['job_duration'] )
            info[uuid]['marathon_ratio_progress'] = current_cpu_percent / desired_cpu_percent 
            #prinrequeRstst( 'current_cpu_host: ' + str(current_cpu_host) +', current_cpu: ' + str(current_cpu) +', current_cputime_accumulated: ' + str(allinfo[ 'marathon' ][uuid]['current_cputime_accumulated']) +', desired_cputime_accumulated: ' + str( allinfo[ 'marathon' ][uuid]['desired_cputime_accumulated'] ))
        
            print('\main_marathon of '+ info[uuid]['name'] +' --> job_duration = '+ str(info[uuid]['job_duration']) + ', desired_cputime_accumulated = ' + str(info[uuid]['desired_cputime_accumulated'])+ '\n') 

            # Sends metrics to Monasca
            metrics_desired = [
                get_metric_current_cpu (uuid, info),
                #get_metric_job_duration (uuid, info),
                get_metric_current_cputime_accumulated (uuid, info),
                get_metric_desired_cputime_accumulated (uuid, info),
                get_metric_marathon_ratio_progress( uuid, info),
                get_metric_marathon_cputime_current_vs_desired( uuid, info)
            ]
            #print('\ninfo[uuid]: ' + json.dumps(info[uuid]) + '\n')

            send_metrics( metrics_desired ) 

            # Check state
            state = check_state_marathon (info[uuid]['current_cputime_accumulated'], info[uuid]['desired_cputime_accumulated'], info[uuid]['desv_deadline'])
            logger.info( 'Marathon - STATE of '+ jobname +' is ' + state)
            
            needsSend = False
            # Elasticity?
            if (state == 'OVER_PERFORMANT'):
                needsSend, job = alarm_state_inf( info [ uuid ] , job_json)
            elif (state == 'UNDER_PERFORMANT'):
                needsSend, job = alarm_state_sup( info [ uuid ] , job_json)
            
            if needsSend:
                marathon.updateJob(job)
                info[uuid]['init_time'].append( time.time() )
                print('Anyadiendo a info[uuid][init_time]...') 
                info[ uuid ]['current_cputime_accumulated_all'] = current_cpu
                print("info[ uuid ]['current_cputime_accumulated_all']: " + str(info[ uuid ]['current_cputime_accumulated_all']))
            
        if (job_json == {}): # app is not running
                logger.info('Marathon - JOB  '+ jobname +' not running. Deleting...')
                del info[uuid]
    mutex.release()

# FLASK
    
@app.route('/')
def api_root():
    return 'Welcome' + '\n'

@app.route('/updateTask', methods = ['POST'])
def api_updateTask():
    if request.headers['Content-Type'] == 'text/plain':
        return "Text Message: " + request.data 
    elif (request.headers['Content-Type'] == 'application/json' ):
        update_task_chronos( request.json )   
        return "JSON Message: " + json.dumps(request.json) + "\n"
    else:
        return "415 Unsupported Media Type"   

@app.route('/initTask', methods = ['POST'])
def api_initTask():
    if request.headers['Content-Type'] == 'text/plain':
        return "Text Message: " + request.data 
    elif (request.headers['Content-Type'] == 'application/json' ):
        init_task ( request.json )   
        return "JSON Message: " + json.dumps(request.json) + "\n"
    else:
        return "415 Unsupported Media Type"  

@app.route('/initMarathonApp', methods = ['POST'])
def api_initMarathonApp():
    if request.headers['Content-Type'] == 'text/plain':
        return "Text Message: " + request.data 
    elif (request.headers['Content-Type'] == 'application/json' ):
        init_marathon_app( request.json )   
        return "JSON Message: " + json.dumps(request.json) + "\n"
    else:
        return "415 Unsupported Media Type"   

@app.route('/endMarathonApp', methods = ['POST'])
def api_endMarathonApp():
    if request.headers['Content-Type'] == 'text/plain':
        return "Text Message: " + request.data 
    elif (request.headers['Content-Type'] == 'application/json' ):
        end_marathon_app( request.json )   
        return "JSON Message: " + json.dumps(request.json) + "\n"
    else:
        return "415 Unsupported Media Type"   



if __name__ == '__main__':
    get_arguments()
    init_log(logDirectory)
    thread_main_marathon = InfiniteTimer(monitoring_period, main_marathon)
    thread_main_marathon.start()
    main_marathon()
    app.run(port=api_rest_port, host = api_rest_ip) 
    thread_main_marathon.cancel()
