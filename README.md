# Vertical Elasticity in Marathon

These archives leverage the use of checkpointing in Docker to implement statefull vertical elasticity in Marathon. It uses:
- CRUE for the checkpointing.
- MONASCA for the recording of the QoS and the cpu time.

# Embedding the applications

First embedd your application dependencies in a Docker container. Take note of the image and the command you want to execute. Second, create a Marathon job file that uses the "shell_trap_v4.sh" script to run such command. The syntax of this file is:

shell_trap_v4.sh <<app_name>> <<checkpoint_dir>> <<container_image>> <<container_cmd>>

Where <<app_name>> is the name that will be used for the checkpointing, a file that contains the container id and denotes the existence of a previous checkpoint and the dimension "name" in Monasca metrics. <<checkpoint_dir>> is a directory path accessible by all nodes. By <<container_image>> and <<container_cmd>> we refer to your container image and command.

The Marathon job description in JSON must include the next terms:

- "cmd": "<<your_location>>/shell_trap_v4.sh <<app_name>> <<checkpoint_dir>> <<container_image>> <<container_cmd>>
    For example: /home/users/myuser/checkpointing/sheel_trap_v4.sh /home/users/myuser/checkpointing/checkpoint_dir eubrabigsea/marathonvetest \" /bin/bash -c 'time /mtlinpack' \" "
- "id": "<<app_name>>"
- "qos": { "cpuqosms": 747000, "qosdeadlinesec": 900  }
    "cpuqosms" denotes the miliseconds that we want to guarantee that will be given to our application in the period of "qosdeadlinesec" seconds.
In the example we use a restart delay of 10 minutes ("backoffSeconds" :600).

# Submission and monitoring.

You must use the submit.sh script provided as it registers the starting point, QoS and Deadline in MONASCA, so the rest of the system can work.

The metrics registered are:
- container.start, timestamp in seconds since Epoch of the starting of the task.
- container.cpu.qos, number of miliseconds that should be guaranteed by the deadline
- container.cpu.qos.deadline, timestamp in seconds since Epoch for the deadline.

The script submission_error.sh, can compute for a given application name (syntax: submission_error.sh <<app_name>>) if the application is progressing beyond / on / above plan, with a tolerance of 10%. 


