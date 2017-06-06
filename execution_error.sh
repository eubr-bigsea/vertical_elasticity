#!/bin/bash

# SYNTAX: 
#  execution_error.sh <<app_id>>

#!/bin/bash
MASTERIP=158.42.104.229

# First argument is the json file

#   CMD_LINE=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'cmd'"]'`
#   QOS_CPU=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'qos'"]["'cpuqosms'"]'`
#   QOS_DEADLINE=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'qos'"]["'qosdeadlinesec'"]'`
#   APP_ID=`cat $1 | python -c 'import json,sys;obj=json.load(sys.stdin);print obj["'id'"]'`
   APP_ID=$1

   CURR_TIME=`date +"%s"`

   LAST_JOB_START=`monasca metric-statistics --dimensions name=linpacktest2 --merge_metrics container.start avg -14400 | tail -2 | head -1 | awk -F "|" '{  print $5 }' | awk -F "." '{ print $1 }' `

   # Compute Period_Secs to accumulate the cpu from the start of the job, in seconds
   echo "Current date: $CURR_TIME"
   echo "Last Job Start: $LAST_JOB_START"
   PERIOD_SECS=$(( ( $CURR_TIME - $LAST_JOB_START ) + 7200 ))
   echo "Seconds for period: $PERIOD_SECS"

   # Compute starting time to start from the job start, in minutes
   BACK_MINS=$(( ($CURR_TIME - $LAST_JOB_START)/60 + 1 ))
   echo "Back Mins: $BACK_MINS"

   # Extract the last column from the output and trim the decimal part
   QOS=`monasca metric-statistics --dimensions "name=$APP_ID" --merge_metrics container.cpu.qos avg -$BACK_MINS | tail -2 | head -1 | awk -F "|" '{ print $5 }' | awk -F "." '{ print $1 }'`
   echo "QoS: $QOS"

   # Extract the last column from the output and trim the decimal part
   DEADLINE=`monasca metric-statistics --dimensions "name=$APP_ID" --merge_metrics container.cpu.qos.deadline avg -$BACK_MINS | tail -2 | head -1 | awk -F "|" '{ print $5 }' | awk -F "." '{ print $1 }'`
   echo "Deadline: $DEADLINE"

   ELAPSED_USER_TIME=`monasca metric-statistics --dimensions "name=$APP_ID" --merge_metrics container.cpu.user_time --period $PERIOD_SECS sum -$BACK_MINS | tail -2 | head -1 | awk -F "|" '{ print $5 }' | awk -F "." '{ print $1 }'`
   ELAPSED_SYS_TIME=`monasca metric-statistics --dimensions "name=$APP_ID" --merge_metrics container.cpu.system_time --period $PERIOD_SECS sum -$BACK_MINS | tail -2 | head -1 | awk -F "|" '{ print $5 }' | awk -F "." '{ print $1 }'`

   ELAPSED_TOTAL_TIME=$(( $ELAPSED_USER_TIME + $ELAPSED_SYS_TIME ))
   echo "Total time: $ELAPSED_USER_TIME + $ELAPSED_SYS_TIME = $ELAPSED_TOTAL_TIME"

   if (( $(echo "$DEADLINE > $CURR_TIME" | bc -l) )) ;  then
     EXPECTED_PROGRESS=$(echo "$QOS * ( $DEADLINE - $CURR_TIME ) / ($DEADLINE - $LAST_JOB_START)" | bc -l )
     echo "Expected Progress: $QOS * ( $DEADLINE - $CURR_TIME ) / ($DEADLINE - $LAST_JOB_START) = $EXPECTED_PROGRESS"
  
     RATIO_PROGRESS=$(echo "$ELAPSED_TOTAL_TIME / $EXPECTED_PROGRESS" | bc -l )
     echo "Ratio: $RATIO_PROGRESS"
     if (( $(echo "$RATIO_PROGRESS < 0.9" | bc -l) )); then
       echo "UNDER PERFORMANT"
     else 
       if (( $(echo "$RATIO_PROGRESS > 1.1" | bc -l) )); then
         echo "OVER PERFORMANT"
       else
         echo "ON PLAN"
       fi
     fi     
   else 
     echo "DEADLINE OVERPASSED"
   fi     
 

