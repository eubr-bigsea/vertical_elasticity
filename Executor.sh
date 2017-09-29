#!/bin/bash 

set -x 

FORMER_CONTAINER_ID=""
STATS_CONTAINER_ID=""

CONTAINER_NAME=$1
CHECKPOINT_NAME=${CONTAINER_NAME}
CHECKPOINT_DIR=$2
CONTAINER_IMAGE=$3
START_URL_WEBHOOK=$4
END_URL_WEBHOOK=$5
DOCKER_OPTIONS=$6
CONTAINER_CMD=${*:7}  

# Variables
# CONTAINER_NAME: Name of the application. Typically, the id declared in the application JSON. It is used for creating a file in the checkpointing directory with the container id. If it exists, the script assumes that a checkpoint has been created.
# CHECKPOINT_NAME: Name of the checkpoint. Only one checkpoint for container is created. Each time a job is relaunched, a new container is created, so there is no issue in repeating the name.
# CHECKPOINT_DIR: The directory (accessible across al the Mesos Agents), where the checkpoints will be created.
# CONTAINER_IMAGE: Name of the container image. 
# CONTAINER_ID: Long id of the Docker container, as retrieved from the docker run command, and stored in $CHECKPOINT_DIR/.$CONTAINER_NAME
# START_URL_WEBHOOK and END_URL_WEBHOOK: paths of Supervisor REST API 
# DOCKER_OPTIONS: options for container creation
# FORMER_CONTAINERID: Long id of the container that was checkpointed.  
# child: the pid of the monitoring process

_term() { 
  echo "We caught SIGTERM signal!" 
  # Create checkpoint
  echo "Creating checkpoint..."
  sudo docker checkpoint create --checkpoint-dir=$CHECKPOINT_DIR $CONTAINER_NAME $CHECKPOINT_NAME
  echo "Checkpoint created"
  # Kill container
  KILLED=1
  kill -TERM "$child" 2>/dev/null
  # Remove
  sudo docker rm -f $CONTAINER_NAME
}

_wait_container() {
  CONTAINER_ID=$1
  sudo docker logs -f $CONTAINER_ID
}

_run_new_docker() {
  CHECKPOINT_DIR=$1
  CONTAINER_NAME=$2
  CONTAINER_IMAGE=$3
  CONTAINER_CMD=${@:4}

  echo "New execution"
  echo "    CONTAINER_NAME: $CONTAINER_NAME"
  echo "    CHECKPOINT_DIR: $CHECKPOINT_DIR"
  echo "    CONTAINER_IMAGE: $CONTAINER_IMAGE"
  echo "    CONTAINER_CMD: $CONTAINER_CMD"
  echo "    DOCKER_OPTIONS: $( echo $DOCKER_OPTIONS)"
  echo " "

  docker rm -f $CONTAINER_NAME
  # Passing properly the arguments when there are quotes is complex. See the example
  CMD="sudo docker run -di --name $CONTAINER_NAME $(echo $DOCKER_OPTIONS) $CONTAINER_IMAGE"
  echo "$CMD $CONTAINER_CMD > $CHECKPOINT_DIR/.$CONTAINER_NAME"
  echo $CONTAINER_CMD | xargs $CMD > $CHECKPOINT_DIR/.$CONTAINER_NAME
  CONTAINER_ID=`cat $CHECKPOINT_DIR/.$CONTAINER_NAME`
  echo "$CONTAINER_ID" > "$CHECKPOINT_DIR"/.stats_"$CONTAINER_NAME"
}


_run_chkped_docker() {
  CHECKPOINT_DIR=$1
  CONTAINER_NAME=$2
  CONTAINER_IMAGE=$3
  CONTAINER_CMD=${@:4}

  FORMER_CONTAINER_ID=`cat $CHECKPOINT_DIR/.$CONTAINER_NAME`
  STATS_CONTAINER_ID=`cat "$CHECKPOINT_DIR"/.stats_"$CONTAINER_NAME"`

  echo "Trying to restore checkpoint from $FORMER_CONTAINER_ID"
  docker rm -f $CONTAINER_NAME

  retries=0
  maxretries=10
  while [ ! -e "$CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints/$CONTAINER_NAME/config.json" ] && [ "$retries" -lt "$maxretries" ];  
  do
    echo "WARNING: Checkpoint $CONTAINER_NAME not exists in $CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints. Retrying in 10 seconds.."
    retries=$((retries + 1))
    sleep 10
  done

  if [ -e "$CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints/$CONTAINER_NAME/config.json" ]; then  
    echo "Checkpoint found, restoring..."
    #sudo docker create --name $CONTAINER_NAME $(echo $DOCKER_OPTIONS) $CONTAINER_IMAGE /bin/bash >  $CHECKPOINT_DIR/.$CONTAINER_NAME
    #CONTAINER_ID=`cat $CHECKPOINT_DIR/.$CONTAINER_NAME`
    CONTAINER_ID=$(sudo docker create --name $CONTAINER_NAME $(echo $DOCKER_OPTIONS) $CONTAINER_IMAGE /bin/bash)
    sudo docker start --checkpoint-dir=$CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints --checkpoint=$CONTAINER_NAME $CONTAINER_NAME
    if [ $? -ne 0 ]; then
      echo "ERROR: Restore checkpoint $CONTAINER_NAME"
      exit 1 
    fi 
    sleep 15
    echo "Removing checkpoint $CHECKPOINT_NAME..."
    sudo docker checkpoint rm --checkpoint-dir=$CHECKPOINT_DIR $CONTAINER_NAME $CHECKPOINT_NAME 
    echo "Removing $CHECKPOINT_DIR/$FORMER_CONTAINER_ID..."
    rm -rf $CHECKPOINT_DIR/$FORMER_CONTAINER_ID
    echo "Contained restored succsesfully"
    echo "$CONTAINER_ID" > $CHECKPOINT_DIR/.$CONTAINER_NAME
    echo "Creating directory /opt/mycgroup/cpuacct/$CONTAINER_ID for soft link of cpuacct.stats"
    mkdir -p /opt/mycgroup/cpuacct/$CONTAINER_ID
    ln -s /sys/fs/cgroup/cpuacct/docker/$STATS_CONTAINER_ID/cpuacct.stat /opt/mycgroup/cpuacct/$CONTAINER_ID/cpuacct.stat
    # Prueba
    cat /opt/mycgroup/cpuacct/$CONTAINER_ID/cpuacct.stat
  else
    echo "ERROR: Checkpoint $CONTAINER_NAME not exists in $CHECKPOINT_DIR/$FORMER_CONTAINER_ID/checkpoints."
    #_notify_webhook_end
    exit 1 
  fi  
}

_terminate() {
  # If the Container has not been killed but simply it finished, the checkpoint should be removed
  if [ $KILLED -eq 0 ]; then
    _notify_webhook_end 
    rm $CHECKPOINT_DIR/.$CONTAINER_NAME
    rm "$CHECKPOINT_DIR"/.stats_"$CONTAINER_NAME"
  fi
}

_notify_webhook_end(){
  ENDED_AT=$(date +%s) 
  /usr/bin/curl $END_URL_WEBHOOK -H 'Content-type: application/json' -d @<(cat <<EOF
{
  "uuid": "$CONTAINER_NAME",
  "finished_at": "$ENDED_AT"
}
EOF
) 
}

_notify_webhook_start(){
  STARTED_AT=$(date +%s)
  /usr/bin/curl $START_URL_WEBHOOK -H 'Content-type: application/json' -d @<(cat <<EOF
{
  "uuid": "$CONTAINER_NAME",
  "started_at": "$STARTED_AT"
}
EOF
) 
}
# -------------------------------------------------------------- #
# ---------------------------- MAIN ---------------------------- #
# -------------------------------------------------------------- #



KILLED=0

trap _term SIGTERM

if [ ! -f $CHECKPOINT_DIR/.$CONTAINER_NAME ]; then
  _notify_webhook_start 
  _run_new_docker $CHECKPOINT_DIR $CONTAINER_NAME $CONTAINER_IMAGE $CONTAINER_CMD
else
  _run_chkped_docker $CHECKPOINT_DIR $CONTAINER_NAME $CONTAINER_IMAGE $CONTAINER_CMD
fi

CONTAINER_ID=`cat $CHECKPOINT_DIR/.$CONTAINER_NAME`
_wait_container $CONTAINER_ID &

child=$! 
wait "$child"

_terminate 
echo "Execution ended"



