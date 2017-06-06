#!/bin/bash 

# Combined script that will start a new container if no previous checkpoints have been registered
# It will use a file named .<<app_name>> with the last id . It is therefore very important to remove it for a new execution.
# app_name will come from the first argument

# it will make the checkpointing when terminated
# This version does not poll, simply blocks on the log.


## SYNTAX
#   shell_trap_v4.sh <<app_name>> <<checkpoint_dir>> <<container_image>> <<container_cmd>>
#  
# IMPORTANT!!! PASSING PROPERLY THE ARGUMENTS IS TRICKY!!! SEE EXAMPLE

# e.g.:
#   shell_trap_v4.sh linpacktest /home/users/iblanque/interacting/checkpointing/checkpoint_dir eubrabigsea/marathonvetest "/bin/bash -c 'time /mtlinpack'"

APP_NAME=$1
CHECKPOINT_NAME=${APP_NAME}
# e.g. CHECKPOINT_DIR=/home/users/iblanque/interacting/checkpointing/checkpoint_dir
CHECKPOINT_DIR=$2
POLLING_TIME=60
# e.g. CONTAINER_IMAGE=eubrabigsea/marathonvetest
CONTAINER_IMAGE=$3
# e.g. CONTAINER_CMD="/bin/bash -c 'time /mtlinpack'"
CONTAINER_CMD=${*:4}

# Variables
# APP_NAME: Name of the application. Typically, the id declared in the application JSON. It is used for creating a file in the checkpointing directory with the container id. If it exists, the script assumes that a checkpoint has been created.
# CHECKPOINT_NAME: Name of the checkpoint. Only one checkpoint for container is created. Each time a job is relaunched, a new container is created, so there is no issue in repeating the name.
# CHECKPOINT_DIR: The directory (accessible across al the Mesos Agents), where the checkpoints will be created.
# CONTAINER_ID: Long id of the Docker container, as retrieved from the docker run command, and stored in $CHECKPOINT_DIR/.$APP_NAME
# child: the pid of the monitoring process
# FORMER_CONTAINERID: Long id of the container that was checkpointed.  


_term() { 
  echo "We caught SIGTERM signal!" 
  sudo docker checkpoint create --checkpoint-dir $CHECKPOINT_DIR $CONTAINER_ID $CHECKPOINT_NAME
  KILLED=1
  kill -TERM "$child" 2>/dev/null
}

_wait_container() {
  CONTAINER_ID=$1
  sudo docker logs -f $CONTAINER_ID
}

_run_new_docker() {
  CHECKPOINT_DIR=$1
  APP_NAME=$2
  CONTAINER_IMAGE=$3
  CONTAINER_CMD=${@:4}

  echo "New execution"
  echo "    APP_NAME: $APP_NAME"
  echo "    CHECKPOINT_DIR: $CHECKPOINT_DIR"
  echo "    CONTAINER_IMAGE: $CONTAINER_IMAGE"
  echo "    CONTAINER_CMD: $CONTAINER_CMD"
  echo " "

  # Passing properly the arguments when there are quotes is complex. See the example
  CMD="sudo docker run -dit --name $APP_NAME --security-opt=seccomp:unconfined $CONTAINER_IMAGE"
  echo "$CMD $CONTAINER_CMD > $CHECKPOINT_DIR/.$APP_NAME"
  echo $CONTAINER_CMD | xargs $CMD > $CHECKPOINT_DIR/.$APP_NAME
  #sudo docker run -dit --name $APP_NAME --security-opt=seccomp:unconfined $CONTAINER_IMAGE $CONTAINER_CMD) > $CHECKPOINT_DIR/.$APP_NAME
  CONTAINER_ID=`cat $CHECKPOINT_DIR/.$APP_NAME`
}


_run_chkped_docker() {
  CHECKPOINT_DIR=$1
  APP_NAME=$2
  CONTAINER_IMAGE=$3
  CONTAINER_CMD=${@:4}
  FORMER_CONTAINER_ID=`cat $CHECKPOINT_DIR/.$APP_NAME`

  echo "Restoring checkpoint from $FORMER_CONTAINER_ID"
  sudo docker run -dit --name "$APP_NAME" --security-opt=seccomp:unconfined $CONTAINER_IMAGE /bin/bash >  $CHECKPOINT_DIR/.$APP_NAME
  CONTAINER_ID=`cat $CHECKPOINT_DIR/.$APP_NAME`
  # Wait detached run 
  sleep 4
  sudo docker start --checkpoint $CHECKPOINT_NAME --checkpoint-dir  $CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints $CONTAINER_ID
  sleep 2
}

_terminate() {

# If the Container has not been killed but simply it finished, the checkpoint should be removed
if [ $KILLED -eq 0 ]; then
  rm $CHECKPOINT_DIR/.$APP_NAME
  sudo docker checkpoint rm --checkpoint-dir $CHECKPOINT_DIR $CONTAINER_ID $CHECKPOINT_NAME
fi
}

#set -x

KILLED=0

trap _term SIGTERM

#APP_NAME=$1
#CHECKPOINT_NAME=${APP_NAME}
#CHECKPOINT_DIR=/home/users/iblanque/interacting/checkpointing/checkpoint_dir
#POLLING_TIME=60
#CONTAINER_IMAGE=eubrabigsea/marathonvetest
#CONTAINER_CMD=/mtlinpack

if [ ! -f $CHECKPOINT_DIR/.$APP_NAME ]; then
  _run_new_docker $CHECKPOINT_DIR $APP_NAME $CONTAINER_IMAGE $CONTAINER_CMD
else
  _run_chkped_docker $CHECKPOINT_DIR $APP_NAME $CONTAINER_IMAGE $CONTAINER_CMD
fi

CONTAINER_ID=`cat $CHECKPOINT_DIR/.$APP_NAME`
_wait_container $CONTAINER_ID &

child=$! 
wait "$child"

echo "Execution ended"
_terminate




