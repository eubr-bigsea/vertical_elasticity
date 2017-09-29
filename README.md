# Vertical Elasticity on Marathon and Chronos Mesos frameworks

## Overview 

<p align="justify">
The main objective of this work is implements a tool that executes a <b>Dockerized Job</b> in order to accomplish a give <b>Quality of Service</b> (<b>QoS</b>) for <a href="https://mesos.apache.org/">Apache Mesos</a> Frameworks: <a href="https://mesos.github.io/chronos/">Chronos</a>: or <a href="https://mesosphere.github.io/marathon/">Marathon</a>. To get this, the tool <b>modifies resource allocation</b> for each application. Furthemore, the tool sends metrics to <a href="https://wiki.openstack.org/wiki/Monasca">Monasca OpenStack</a>. 
</p>

There are two possibles scenarios:
- Chronos. Guarantee that the individual executions of the application are completed in a given.
- Marathon. Guarantee that a minimum share of the CPU time has been allocated to that application.

## Components 

### Launcher 
<p align="justify">
<b>Launcher</b> is the component in charge of the submission of the job. Jobs are specified using JavaScript Object Notation (JSON) format, and <b>Launcher</b> assigns each job an unique identifier (UUID). According to the scenario’s specification, <b>Launcher</b> will submit the job with a modified job specification. Once submitted, <b>Launcher</b> will send to the <b>Supervisor</b> relevant information for the monitoring and scaling the application (e.g. the application deadline).


Dependencies:
- Python module <i>requests</i>

CLI parameters:
- -j <i>\<job-file\></i>. Required parameter. <i>\<job-file\></i> contains the job specification in JSON format. This specitication must contain the correct fields for each framework (you can check this creating a job by framework REST API) and information about QoS (it is described below).
- -m <i>\<credentials-Marathon\></i>. Required parameter (if -c is not being used). <i>\<credentials-Marathon\></i> contains the credentials for Marathon and it is described below.
- -c <i>\<credentials-Chronos\></i>. Required parameter (if -m is not being used). <i>\<credentials-Chronos\></i> is like <i>\<credentials-Marathon\></i>
- -i <i>\<supervisor-url\></i>. Required parameter. <i>\<supervisor-url\></i> it is the URL of the Supervisor REST API (e.g. “http://10.0.0.2:30000”).

Other parameters used: 
- <b>executor_path</b>: absolute path of the component <b>Executor</b> in Mesos agent nodes.
- <b>checkpoint_dir</b>: shared path between Mesos agent nodes where checkpoints will be stored.
- <b>taskKillGracePeriodSeconds</b>: quantity of seconds before Marathon executor remove the job once termination signal is received.

These parameters are in the main of [Launcher.py](Launcher.py#200).
</p>

### Supervisor
<p align="justify">
<b>Supervisor</b> is a REST service that receives the information sent by <b>Launcher</b> and the containers. According to the scenario’s specification, it monitors the application in order to scale up and down the resources, according to an agreed quality of service. Furthermore, Supervisor sends metrics to Monasca for its visualization.


Dependencies:
- Python module <i>requests</i>
- Python module <i>Flask</i> 

CLI parameters:
- -m <i>\<credentials-Marathon\></i>. Required parameter. <i>\<credentials-Marathon\></i> contains the credentials for Marathon and it is described below.
- -c <i>\<credentials-Chronos\></i>. Required parameter. <i>\<credentials-Chronos\></i> is like <i>\<credentials-Marathon\></i>
- -o <i>\<credentials-OpenStack\></i>. Required parameter. <i>\<credentials-OpenStack\></i> contains the credentials for <a href="https://wiki.openstack.org/wiki/Keystone">KeyStone</a> and the URL of Monasca. The file is described below.
- -i <i>\<rest-ip\></i>. Optional parameter. Default value is “0.0.0.0”.
- -p <i>\<rest-port\></i>. Optional parameter. Default value is “30000”.

Other parameters used: 
- <b>logDirectory</b>: absolute path of the directory where <b>Supervisor</b> stores their log.
- <b>cpu_max_slave</b>: maximum shared CPU time available in Mesos agent node.
- <b>cpu_min_slave</b>: minimum shared CPU time available in Mesos agent node.
- <b>monitoring_period</b>: Monitoring period of Marathon applications by <b>Supervisor</b>.
- <b>cpu_increment</b>
- <b>cpu_decrement</b>

These parameters in [Supervisor.py](Supervisor.py#20).
</p>

## QoS definition
<p>
QoS is defined in the job specification file. Three parameters are needed:

- <b>duration</b>: expected duration of one iteration of the application in seconds.
- <b>desv_deadline</b>: maximum overprogress percentage.
- <b>deadline</b>: interval of time given to the system for complete the job.

``` json
{
        "qos" : {
                "duration": 600,
                "desv_deadline": 0.8,
                "deadline": 350

        }
}
```

</p>

## Credential files
The credential files required for the correct performance of the modules described above are: 
#### Chronos and Marathon
``` json
{
        "url" : "http://IP:PORT",
        "user" : "USER",
        "password" : "PASSWD"
}
```

#### Monasca
``` json
{
        "keystone_url" : "http://IP:PORT",
        "monocasca_client_url" : "http://IP:PORT",
        "username" : "USER",
        "password" : "PASSWD",
        "project_name" : "myprojectname"
}
```
