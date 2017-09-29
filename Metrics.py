def get_metric_remaining_iterations(uuid, info):
    metric = {
            'name': 'remaining_iterations',
            'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ] },
            'value':  int( info[ uuid ][ 'iterations' ] )
    }
    return metric

def get_metric_prediction_vs_deadline(uuid, info):
    metric = {
        'name': 'prediction_vs_deadline',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ] },
        'value':  int( info[ uuid ]['prediction'] - info[ uuid ]['deadline'] )
    } 
    return metric  

def get_metric_prediction (uuid, info):
    metric = {
        'name': 'prediction_deadline',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value':  info[ uuid ][ 'prediction' ]
    } 
    return metric  

def get_metric_deadline (uuid, info):
    metric = {
        'name': 'deadline',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ] , 'uuid': info[ uuid ][ 'uuid' ]},
        'value':  int( info[ uuid ][ 'deadline' ] )
    }    
    return metric

def get_metric_timestamp_finished (uuid, info):
    metric = {
        'name': 'timestamp_finished',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ] },
        'value':  int( info[ uuid ][ 'current' ] )
    }   
    return metric

def get_metric_current_cpu (uuid, info):
    metric = {
        'name': 'current_cpu',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': info[ uuid ]['current_cpu'] 
    }   
    return metric

def get_metric_job_duration (uuid, info):
    metric = {
        'name': 'last_job_duration',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': info[ uuid ]['last_job_duration'] 
    }   
    return metric

def get_metric_current_cputime_accumulated (uuid, info):
    metric = {
        'name': 'current_cputime_accumulated',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': info[ uuid ]['current_cputime_accumulated'] 
    }   
    return metric


def get_metric_desired_cputime_accumulated (uuid, info):
    metric = {
        'name': 'desired_cputime_accumulated',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': info[ uuid ]['desired_cputime_accumulated'] 
    }   
    return metric

def get_metric_marathon_ratio_progress( uuid, info):
    metric = {
        'name': 'marathon_ratio_progress',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': info[ uuid ]['marathon_ratio_progress'] 
    }   
    return metric

def get_metric_marathon_cputime_current_vs_desired( uuid, info):
    value = info[ uuid ]['desired_cputime_accumulated'] - info[ uuid ]['current_cputime_accumulated'] 
    metric = {
        'name': 'marathon_cputime_current_vs_desired',
        'dimensions': { 'jobname': info[ uuid ][ 'name' ], 'framework': info[ uuid ][ 'framework' ], 'uuid': info[ uuid ][ 'uuid' ]},
        'value': value
    }   
    return metric