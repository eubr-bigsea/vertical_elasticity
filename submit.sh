#!/bin/bash
MASTERIP=158.42.104.229

# First argument is the json file

_publish_start() {

  echo "QOS: $1"
  echo "QOS_DEADLINE: $2"
  echo "shell_trap: $3"
  echo "id: $4"
  echo "chkpdir: $5"
  echo "container image: $6"
  echo "container cmd: ${@:7}"

  CURR_DATE=`date +"%s"`

  TASK_ID="$4_${CURR_DATE}"
  echo ${TASK_ID}

#  MON_CMD=$(printf "{\"name\":\"container.start\",\"dimensions\":{\"name\":\"%s\",\"image\":\"%s\"},\"timestamp\":%s,\"value\":%s}" "$4" "$6" "$CURR_DATE" "$CURR_DATE" )
#  echo "monasca metric-create-raw $MON_CMD"
#  monasca metric-create-raw $MON_CMD

   monasca metric-create --dimensions "name=$TASK_ID, image=$6" container.start $CURR_DATE
   monasca metric-create --dimensions "name=$TASK_ID, image=$6" container.cpu.qos $QOS_CPU
   monasca metric-create --dimensions "name=$TASK_ID, image=$6" container.cpu.qos.deadline $(( $CURR_DATE + $QOS_DEADLINE ))

}

CMD_LINE=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'cmd'"]'`
QOS_CPU=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'qos'"]["'cpuqosms'"]'`
QOS_DEADLINE=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'qos'"]["'qosdeadlinesec'"]'`

_publish_start $QOS_CPU $QOS_DEADLINE $CMD_LINE



curl -u ubuntu:ubuntu_secret -X POST -H 'Content-Type: application/json'  $MASTERIP:8080/v2/apps --data @$1
