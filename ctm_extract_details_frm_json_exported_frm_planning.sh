#!/bin/bash

#Script is to extract feilds from the JSON file, exported from Control-M Planning section
#Extracted feilds are "SubApp, Folder, Job, Type, runas, description, resourcepool"
# Useful to get statistics 
#This script require JQ package installed in Linux Machine
#Usage: ctm_extract_details_frm_json_exported_frm_planning.sh /path/to/fileName.json
# Author:       Suresh Kumar Nagaram 	ns0861989@gmail.com
# Date:         Apr 1 2024
# Version:      v1.0

fileName=$1
allFolders=$(jq 'paths as $path | select(getpath($path) | objects | .Type == "Folder" or .Type == "SimpleFolder") | $path[-1]' $fileName)
allJobs=$(jq 'paths as $path | select(getpath($path) | objects | .Type | strings | test("Job*")) | $path[-1]' $fileName)
allResourcePools=$(jq 'paths as $path | select(getpath($path) | objects | .Type | strings | test("Resource:Pool")) | $path[-1]' $fileName)
folderCount=$(echo $allFolders | wc -w)
jobCount=$(echo $allJobs | wc -w)
resPoolCount=$(echo $allResourcePools | wc -w)
echo "SubApp, Folder, Job, Type, runas, description, resourcepool"
echo -e ",Folder count: $folderCount, Total Jobs Count: $jobCount,,,, Total Pools Count: $resPoolCount"
totJobCount=0
for folder in $allFolders
        do
                folderName=$folder
                keysInFolder=$(jq --argjson v $folder '.[$v] | keys[]' $fileName)
                jobInFolder=$(jq --argjson v $folder '.[$v] | keys[] ' $fileName | grep -oF -f <(echo "$allJobs"))
                jobCount=$(echo $jobInFolder |wc -w)
#               echo -e "FolderName: $folderName, No. of jobs in this folder is: $jobCount"
                totJobCount=$(($totJobCount + $jobCount))
                for job in $jobInFolder
                do
                        jobName=$job
                        keysinJob=$(jq --argjson j $job --argjson f $folder '.[$f].[$j] | keys[]' $fileName)
                        resourcePoolName=$(jq --argjson j $job --argjson f $folder '.[$f].[$j] | keys[]' $fileName | grep -oF -f <(echo "$allResourcePools"))
                        resourcePoolName=$(echo $resourcePoolName | awk '{print $1}')
                        jobType=$(jq --argjson v $job '. | to_entries | .[] | .value.[$v].Type' $fileName | grep -v null )
                        jobType=$(echo $jobType | awk '{print $1}')
                        subApp=$(jq --argjson v $job '. | to_entries | .[] | .value.[$v].SubApplication' $fileName | grep -v null)
                        subApp=$(echo $subApp | awk '{print $1}')
                        runAs=$(jq --argjson v $job '. | to_entries | .[] | .value.[$v].RunAs' $fileName | grep -v null)
                        runAs=$(echo $runAs | awk '{print $1}')
                        description=$(jq --argjson v $job '. | to_entries | .[] | .value.[$v].Description' $fileName | grep -v null)
                        description=$(echo $description | awk '{print $1}')
                        echo "$subApp, $folderName, $jobName, $jobType,  $runAs, $description, $resourcePoolName"
#                       echo "$folderName, $jobName"
                done
done
echo "Total job count is: $totJobCount"
