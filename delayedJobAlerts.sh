#!/bin/bash
#
# Description: Script to find the delay in non-cyclic job's running schedule and trigger mail alert. It takes application name as input argument

# Usage:        ./delayedJobsAlert.sh <appName> <appName> <appName>
# Arguments: Mandatoy argument is app name. Atleast one app name should be passed from the below table
# Must run as "ctmagent"  User name can be modified
# Example:      ./delayedJobsAlert.sh imf eps mdw

# This script require JQ package. Install it through package manager

# Accepted arguments:
#################################################################################
# Accepted names #      Application Full Name                                                           #
#################################################################################
# eps           #       ABC_EPS_GEN_TXEN
# imf           #       IMF
# fin           #       FINSYS
# ctm           #       CTM
# maaes         #       MAAES
# macwdb        #       MACWDB
# madoc         #       MADOC
# mags          #       MAGS_ISIS_IBA_A2A
# wbn           #       MAGS_ISIS_WBN
# mavel         #       MAVEL
# mevel         #       MEVEL
# mdw           #       MDW
# mercator      #       MERCATOR
# pl            #       PLCOM
# urb           #       URB_UserDaily
# us1530        #       US1530_UserDaily
# us            #       US_UserDaily
#
#
# Author:       sureshkumar.nagaram
# Date:         Apr 13 2024
# Version:      v1.2
# V1.0: Updated script to alert just one hour before their schedule time, if at all they are delayed.
# V1.1: Updated script to handel ondemand jobs. With out this, scheduled start time for these jobs are considered as 00:00, as they are unavailable in the file exported during new day. Makes it delayed job since its appearance.

[ "$(whoami)" = "ctmagent" ] || { echo "Invalid user. Please run the script as \"ctmagent\""; exit 1; }  #change the script run as user here in place of "ctmagent"
file_location="/tmp/controlm"	#Location where viewpoint files for reference & temp files stored
echo "$(date)"
ctm=$(command -v ctm 2>/dev/null) || { echo "CTM not found"; exit 1; };
app=$1
today=`date +"%y%m%d"`
yesterday=`date -d "yesterday" '+%y%m%d'`
expected_format="%y%m%d"	#expected date format as yymmdd
ignore_list="" #add sapce seperated case sensitive job names to ignore. like "abc xyz mno"
condition_met=false
delay_threshold=30	#Trigger alerts when job is above this threshold in minutes
bkpCount=1
R='\033[0;31m'	# Makes the STDOUT print in RED color to differentiate between error & normal
W='\033[1;37m'
for i in $@
do
        case "$i" in
                "imf")								#user choosen short name for Application, which will be passed as input arguments to script
                                appl="IMF"			# Actual application name in Control-M
                                ;;
                "eps")
                                appl="ABC_EPS_GEN_TXEN"
                                ;;
                "fin")
                                appl="FINSYS"
                                ;;
                "ctm")
                                appl="CTM"
                                ;;
                "maaes")
                                appl="MAAES"
                                ;;
                "macwdb")
                                appl="MACWDB"
                                ;;
                "madoc")
                                appl="MADOC"
                                ;;
                "mags")
                                appl="MAGS_ISIS_IBA_A2A"
                                ;;
                "wbn")
                                appl="MAGS_ISIS_WBN"
                                ;;
                "mavel")
                                appl="MAVEL"
                                ;;
                "mevel")
                                appl="MEVEL"
                                ;;
                "mdw")
                                appl="MDW"
                                ;;
                "mercator")
                                appl="MERCATOR"
                                ;;
                "pl")
                                appl="PLCOM"
                                ;;
                "urb")
                                appl="URB_UserDaily"
                                ;;
                "us1530")
                                appl="US1530_UserDaily"
                                ;;
                "us")
                                appl="US_UserDaily"
                                ;;
                *) echo "Invalid Input, Please provide valid application name. Given app $i does not exist"; exit 1;;
        esac
current_hrMn=$(date +"%H:%M")

if [ $appl = "IMF" ]	# Choose which rundate file to be reffernced to calculate delays
then
         current_minutes=$(( $(date -d "$current_hrMn" +"%-H") * 60 + $(date -d "$current_hrMn" +"%-M") ))
         if [ "$current_minutes" -ge "930" ]; then	#This application's new scheduled day start at 15:30:00. So current_minutes >= 930. Number of minites from 00:00:00 to 15:30
                 #                   echo "Current time is later than or equal to 3:30 PM"
                    reqDate=$today
            else
                    #                   echo "Current time is earlier than 3:30 PM"
                    reqDate=$yesterday
            fi
            echo -e "${W}\n################ Application is ${appl} & Run Date is ${reqDate} ###############\n"
    else
            if [ $(date -d "$current_hrMn" +"%-H") -ge 7 ]; then	#all other applications new scheduled day starts at 07:00:00
                    reqDate=$today
            else
                    reqDate=$yesterday
            fi
            echo -e "${W}\n################ Application is ${appl} & Run Date is ${reqDate} ###############\n"
fi

if ! date -d "$reqDate" +"$expected_format" &>/dev/null;
then
        echo "Invalid date format. Please save file with date stamp as yymmdd, like 241126"
        exit 1
fi

[ -e ${file_location}/${appl}jobs${reqDate}.json ] || { echo "Invalid file ${file_location}/${appl}jobs${reqDate}.json does not exists.";exit 1; }
#Above line checks the exported view point file exist or not

format_date() {
    # Extract substrings and format into "YYYY-MM-DD HH:MM:SS".
    formatted_date="$(echo "$1" | sed -E 's/(.{4})(.{2})(.{2})(.{2})(.{2})(.{2})/\1-\2-\3 \4:\5:\6/')"
    formatted_date="$(date -d "$formatted_date" +"%b %d %Y %H:%M:%S")"
    echo "${formatted_date}"
}

date_inSec() {
        seco=$(date -d "$(echo "$1" | sed 's/\(....\)\(..\)\(..\)\(..\)\(..\)\(..\)/\1-\2-\3 \4:\5:\6/')" +%s)
        echo $seco
}

"$ctm" run jobs:status::get -s "application=${appl}&status=Wait User,Wait Resource,Wait Host,Wait Workload,Wait Condition&orderDateTo=$reqDate" > ${file_location}/${appl}CurntWaitList.json

count=`jq '.returned' ${file_location}/${appl}CurntWaitList.json`

if [[ $count -eq 0  ]] # True if none of the  jobs and folder are in any wait state
then
        echo "No jobs are being wait state."
else
#       lenth=$(jq '.statuses[] | select(.type=="Job")' ${file_location}/${appl}CurntWaitList.json | grep -w "\"type\": \"Job\"" | wc -l)
        lenth=$(jq '.statuses[] | select(.type=="Job" or .type == "Command")' ${file_location}/${appl}CurntWaitList.json |grep -Ew '"type": "Job"|"type": "Command"' | wc -l)
        echo "Number of waiting jobs are $lenth"

                for folderID in `jq '.statuses[] | select(.type=="Folder").jobId' ${file_location}/${appl}CurntWaitList.json` #for each folder go through each jobs in it
                do
                                folderName=`jq --argjson v $folderID '.statuses[] | select(.jobId==$v and  .type=="Folder").name' ${file_location}/${appl}CurntWaitList.json`
                                echo -e "${W}\n########Folder Name is ${folderName}"
                                jobCount=0

                                for jobID in `jq --argjson v $folderID '.statuses[] | select((.type=="Job" or .type == "Command") and .folderId==$v ).jobId' ${file_location}/${appl}CurntWaitList.json`
                                do
                                                jobName=`jq --argjson v $jobID '.statuses[] | select(.jobId==$v).name' ${file_location}/${appl}CurntWaitList.json`

                                                echo -e "${W}\nJob Name is ${jobName}"
# Ignore list
#                                               for ignoredJob in $ignore_list
#                                                do
#                                                        if [[ $ignoredJob == ${jobName//\"/} ]]
#                                                        then
#                                                                condition_met=true
#                                                                break
#                                                        fi
#                                                done
#                                                if $condition_met; then
#                                                        condition_met=false
#                                                        echo -e "Skipping job as it is in ignore list. Job ID is $jobID.\n"
#                                                        continue
#                                                fi
# Ignore list
                                                curntStartTime=`jq --argjson v $jobID '.statuses[] | select(.jobId==$v).estimatedStartTime[0]' ${file_location}/${appl}CurntWaitList.json`
                                                curntStartTime=`echo ${curntStartTime} | tr -dc [:digit:]`

                                                scheduledStartTime=$(jq --argjson v "$jobID" '.statuses[] | select(.jobId==$v).estimatedStartTime[]' ${file_location}/${appl}jobs${reqDate}.json)
                                                schedTimeSize=$(echo "$scheduledStartTime" | tr -d '"' | wc -w)
                                                curntStartTimeinSec=$(date_inSec "$curntStartTime")
                                                cyclic=`jq --argjson v $jobID '.statuses[] | select(.jobId==$v).cyclic' ${file_location}/${appl}CurntWaitList.json`
												cyclic_folder=`jq --argjson v $folderID '.statuses[] | select(.jobId==$v).cyclic' ${file_location}/${appl}CurntWaitList.json`

# On demand job handelling
                                                if [[ $schedTimeSize -eq 0 ]]
                                                then
                                                        echo "This is on demand job ${jobID}, ${jobName}"
														onDemandJob=$(jq --argjson v "$jobID" '.statuses[] | select(.jobId==$v)' ${file_location}/${appl}CurntWaitList.json) # get on-demand job details from wait-list
														cp ${file_location}/${appl}jobs${reqDate}.json ${file_location}/${appl}jobs${reqDate}_bkpBfr${bkpCount}_${jobID}.json  # backup of reference file.
                                                        jq --argjson newObj "$onDemandJob" '.statuses += [$newObj]' ${file_location}/${appl}jobs${reqDate}.json > ${file_location}/${appl}jobs${reqDate}_ODjob.json  # add on-demand job to reference file
                                                        
                                                        cp -f ${file_location}/${appl}jobs${reqDate}_ODjob.json ${file_location}/${appl}jobs${reqDate}.json
                                                         scheduledStartTime=$(jq --argjson v "$jobID" '.statuses[] | select(.jobId==$v).estimatedStartTime[]' ${file_location}/${appl}jobs${reqDate}.json)
														 bkpCount=$(( bkpCount + 1 ))
														 schedTimeSize=$(echo "$scheduledStartTime" | tr -d '"' | wc -w)
                                                 fi
# On demand job handelling

#                                               if [[ $cyclic == "true" ]]
                                                if [[ $schedTimeSize -gt 1 ]] #if it is a cyclic job, get nearest job's start time
                                                then
                                                        # Initialize variables for nearest match
                                                        nearestMatch=""
                                                        nearestDiff=""
                                                        # Loop through scheduledStartTime array to find nearest match
                                                        for schedTime in ${scheduledStartTime[@]}
                                                        do
                                                                schedTime=`echo ${schedTime} | tr -dc [:digit:]`
                                                                schedTime=$(date_inSec "$schedTime")
                                                                diff=$(( schedTime - curntStartTimeinSec ))
                                                                absDiff=${diff#-}  # Remove the negative sign if present
                                                                if [[ $nearestMatch == "" || $absDiff -lt $nearestDiff ]]
                                                                then
                                                                        nearestMatch=$schedTime
                                                                        nearestDiff=$absDiff
                                                                fi
                                                        done
                                                        scheduledStartTimeinSec=$nearestMatch
                                                        scheduledStartTime=$(date -d "@$nearestMatch" "+%Y%m%d%H%M%S")
                                                        else
                                                        scheduledStartTime=`echo ${scheduledStartTime} | tr -dc [:digit:]`
                                                        scheduledStartTimeinSec=$(date_inSec "$scheduledStartTime")
                                                fi
                                                scheduledStartTime=$(format_date "$scheduledStartTime")
                                                curntStartTime=$(format_date "$curntStartTime")
                                                echo "Scheduled Start Time is $scheduledStartTime"
                                                echo "Estimated Start Time is $curntStartTime"
# Alert just 1Hr before the Jobs scheduled start time
                                                curntTimeinSec=$(date -d "$(date)" +%s)
                                                curntTimeinSecPlus=$((curntTimeinSec + 3600))
                                                if ! [[ $scheduledStartTimeinSec -gt $curntTimeinSecPlus ]]
                                                then
# Alert just 1Hr before the Jobs scheduled start time
                                                if [[ $curntStartTimeinSec != $scheduledStartTimeinSec ]]
                                                then
                                                        timeDiff=$(( ($curntStartTimeinSec - $scheduledStartTimeinSec) / 60 )) # Calculating in minute
                                                        days=$(( timeDiff / 1440 )) # 1440 minutes in a day
                                                        remainingMinutes=$(( timeDiff % 1440 ))
                                                        hours=$(( remainingMinutes / 60 ))
                                                        min=$(( remainingMinutes % 60 ))
                                                        if [[ $cyclic == "false" && $cyclic_folder == "false" ]] #Ignore delay in cyclic Job & folders
                                                        then
                                                                if [[ $timeDiff -gt $delay_threshold ]]
                                                                then
                                                                        ((jobCount++))
                                                                        echo -e "${R}Non-cyclic Job is delayed above the ${delay_threshold}min threshold. Delayed by ${days}Day/s ${hours}Hour/s ${min}Min & jobID is ${jobID}"
                                                                         echo -e "\nJob Name: ${jobName}, Job ID: ${jobID}\nScheduled start time: ${scheduledStartTime}\n Estimated start time: ${curntStartTime}\nDelayed by ${days}Day/s ${hours}Hour/s ${min}Min/s" >> ${file_location}/body3
                                                                         jobStatus=$(jq --argjson v ${jobID} '.statuses[] | select(.jobId==$v and  .type=="Job").status' ${file_location}/${appl}CurntWaitList.json) # Get job status

                                                                         if [ -z "$jobStatus" ]; then
                                                                                 echo -e "Warning: No wait status found for job\n"
                                                                                 echo -e "Warning: No wait status found for job\n" >> ${file_location}/body3
                                                                         elif [[ "$jobStatus" =~ "Wait " ]]; then
                                                                                 #get the wait details
                                                                                 waitDetails=`"$ctm" run job::waitingInfo "${jobID//[\'\"]/}"`
                                                                                 echo -e "Job is in ${jobStatus}"
                                                                                 echo -e "Job is in ${jobStatus}" >> ${file_location}/body3
                                                                                 poolName=$(echo "$waitDetails" | grep -oP "(?<=The Job is waiting for resource ).*(?=, Quantity)")
																				 pool_len=$(echo "$poolName" | wc -l)
#                                                                               echo "Resourcepool Name/s is: ${poolName}"

                                                                                if [ ! -z "$poolName" ]; then	
																						for i in $poolName; do
																							"$ctm" run jobs:status::get -s "resourcePool=$i" > ${file_location}/poolStat.txt
																							poolJob=$(jq '.statuses[] | select(.type!="Folder" and .status=="Executing").name' ${file_location}/poolStat.txt)
																							echo -e "Resource ${i} is being used by the job: ${poolJob}"
																							echo -e "Resource ${i} is being used by the job: ${poolJob}" >> ${file_location}/body3
																						done
                                                                                fi
                                                                                waitEvent=$(echo "$waitDetails" | grep -oP "(?<=The Job is dependant on condition ).*(?=_OK|$)" | sed 's/_OK//g')
#                                                                               echo "Event name is: ${waitEvent}"
                                                                                if [ ! -z "$waitEvent" ]; then
                                                                                        echo -e "Waiting on Event: ${waitEvent}"
                                                                                        echo -e "Waiting on Event: ${waitEvent}" >> ${file_location}/body3
                                                                                fi

                                                                         else
                                                                                 echo -e "Job is in ${jobStatus}\n"
                                                                                 echo -e "Job is in ${jobStatus}\n" >> ${file_location}/body3
                                                                         fi
                                                                else
                                                                        echo -e "Non-cyclic Job delayed by ${timeDiff} Min, which is below than the ${delay_threshold}min threshold, jobID is ${jobID} \n"
                                                                fi
                                                        else

                                                                echo -e "Delayed cyclic jobID is ${jobID} & Job delayed by ${days}Day/s ${hours}Hour/s ${min}Min\n"
                                                        fi
                                                else
                                                        curntTimeinSec=$(date -d "$(date)" +%s)
                                                        crntTime=$(date -d "$(date)" +"%b %d %Y %H:%M:%S")
                                                        curntTimeinSecPlus=$((curntTimeinSec + 1800))
                                                        if [ $curntStartTimeinSec -lt $curntTimeinSec ] #Job start time is < current time but not started
                                                        then
                                                                diffMin=$(( ($curntTimeinSec - $curntStartTimeinSec) % 60 )) #diff in sec
                                                                if [[ $diffMin -gt 1800 ]] #if diffMin is greater than 30min
                                                                then
                                                                        ((jobCount++))
                                                                        echo -e "${R}Job start time is same as scheduled, but delayed WRT current time ${crntTime} by ${diffMin} Sec\n"
                                                                        echo -e "Job Name: ${jobName}, Job ID: ${jobID}\nScheduled start time: ${scheduledStartTime}\n Estimated start time: ${curntStartTime}\nJob start time is same as scheduled, but delayed by ${diffMin} Sec WRT current time ${crntTime}\n" >> ${file_location}/body3
                                                                fi

                                                        else
                                                                echo -e "On time job ${jobID} \n"
                                                        fi
                                                fi
                                        else
# Alert just 1Hr before the Jobs scheduled start time
                                                echo -e "Job's scheduled start time is far away from the current time \"$(date +"%Y-%m-%d %H:%M:%S")\". Job ID is: ${jobID} \n "
                                        fi
# Alert just 1Hr before the Jobs scheduled start time
                                done

                                if (( jobCount != 0 ))
                                then
                                    echo -e "Below jobs from the folder ${folderName} are being delayed:\n$(cat ${file_location}/body3)\n" >> ${file_location}/body1
                                    > ${file_location}/body3
                                fi

        done

        if [ -s "${file_location}/body1" ] #True if file size is > 0
        then
                sed -i "1s/^/This mail is to alert about the jobs delayed more than ${delay_threshold}min from their scheduled start time.\nFor the application \"${appl}\" with run date \"${reqDate}\"\n\n/" "${file_location}/body1"


#       To prevent outlook from removing the line breaks use sendmail or mailx
                (

#                       echo "From: your-email@example.com"             #not mandatory, if not specified uses user@hostname as FROM
                        echo "To: sureshkumar.nagaram@xyz.com"
                        echo "Subject: ${appl} delayed job alert"
                        echo "MIME-Version: 1.0"
                        echo "Content-Type: text/html; charset=UTF-8"
                        echo ""
                        echo "<html><head><style> body { font-family: Consolas, monospace; font-size: 12px; }</style></head><body>"
                        echo "<pre>$(cat ${file_location}/body1)</pre>"  # Preserve line breaks
                        echo "</body></html>"
                ) | sendmail -t

                > ${file_location}/body1
        else
                echo -e "${R}No non-cyclic jobs are being delayed. No mail alert triggered"
        fi




fi
done