#!/bin/bash

# Description: Script to export Control-M current viewpoint for requested application's and save it in a local JSON file
# Invoke this script when an applications new day is started. So that it contains all loded job details
# FIle generated in this script is used as reference to calculate delays in jobs schedule with the script delayedJobAlerts.sh
#
# Usage:        ./export-ViewPoint.sh <appName> <appName> <appName>
# Arguments: Mandatoy argument is app name. Atleast one app name should be given.
#
# Example:      ./export-ViewPoint.sh eps

#Accepted App names	Application Full Name
#
#
# Accepted arguments:
#################################################################################
# Accepted argument names   # 	Application Full Name								#
#################################################################################
# eps		                # 	ABC_EPS_GEN_TXEN	
#imf		                #	IMF	
#fin		                #	FINSYS
#ctm		                #	CTM
#maaes		                #	MAAES
#macwdb		                #	MACWDB
#madoc		                #	MADOC
#mags		                #	MAGS_ISIS_IBA_A2A
#wbn		                #	MAGS_ISIS_WBN
#mavel		                #	MAVEL
#mevel		                #	MEVEL
#mdw		                #	MDW
#mercator	                #	MERCATOR
#pl			                #	PLCOM
#urb		                #	URB_UserDaily
#us1530		                #	US1530_UserDaily
#us			                #	US_UserDaily
#
#
# Author:       sureshkumar.nagaram
# Date:         Feb 26 2024
# Version:      v5.0


[ $# -eq 0 ] && { echo "########### Atleat one APPLICATION NAME (eps/imf etc) must be passed to export the viewpoint ##############"; exit 1; }

today=`date +"%y%m%d"`
ctm=$(command -v ctm 2>/dev/null) || { echo "CTM not found"; exit 1; };
file_location="/tmp/controlm"

for i in $@
do
	case "$i" in
		"imf")
				appl="IMF"
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
					
"$ctm" run jobs:status::get -s "application=${appl}&orderDateTo=${today}" > ${file_location}/${appl}jobs${today}.json

done