#!/bin/bash
#This script will filter the abends based on the given key words and save the result in a file
#Later that file is used to trigger a mail alert on a specific time with either crontab or control-m job
# Useful in non-prod environments

# Set this script while enabling external alerts as described in 
# https://documents.bmc.com/supportu/controlm-saas/en-US/Documentation/Alerts.htm#SettingUpExternalAlerts
#  ctm run alerts:listener:script::set /path/to/ctm_filter_alerts_nonprod.sh

##Author: Suresh Kumar Nagaram

# below block of code is from 
# https://github.com/controlm/automation-api-community-solutions/blob/master/helix-control-m/2-external-monitoring-tools-examples/alerts-data-as-variables/alerts_variables.sh
echo $@ >> /tmp/alertRaw.json
field_names=("eventType" "id" "server" "fileName" "runId" "severity" "status" "time" "user" "updateTime" "message" "runAs" "subApplication" "application" "jobName" "host" "type" "closedByControlM" "ticketNumber" "runNo" "notes")

num_fields=${#field_names[@]}
for i in ${!field_names[@]}; do
   name1=${field_names[$i]}
   name2=${field_names[$i+1]}
   if [ $i != $((num_fields-1)) ] ; then
      value=`echo $* | grep -oP "(?<=${name1}: ).*(?= ${name2}:)"`
      eval "var$i='$value'"
   else
      # If last field, capture until EOL, don´t add last "," and close JSON
      value=`echo $* | grep -oP "(?<=${name1}: ).*(?)"`
      eval "var$i='$value'"
   fi

done
# Above block of code is from "https://github.com/controlm/automation-api-community-solutions/blob/master/helix-control-m/2-external-monitoring-tools-examples/alerts-data-as-variables/alerts_variables.sh"

format_date() {
    # Extract substrings and format into "YYYY-MM-DD HH:MM:SS"
    formatted_date="$(echo "$1" | sed -E 's/(.{4})(.{2})(.{2})(.{2})(.{2})(.{2})/\1-\2-\3 \4:\5:\6/')"
    formatted_date="$(date -d "$formatted_date" +"%b %d %Y %H:%M:%S")"
    echo "${formatted_date}"
}

#Filter the alerts data based on new (I) & keyword (Ended not OK)

if [[ $var0 == "I" && "$var10" == "Ended not OK" ]]
then
        echo ${var14} ${var13} $(format_date "$var7") ${var4} ${var1} ${var6} ${var10} ${var5} >> /tmp/alertDetails_filtered.txt

fi

# This filtered file contents are later used to trigger mail alert on a specific time