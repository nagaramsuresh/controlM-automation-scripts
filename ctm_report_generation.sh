#!/bin/bash
#Export Control-M Reports for the requested application

#Usage:
# ctm_report_generation.sh <applicationName> <applicationName>

# Ex: ctm_report_generation.sh IMF VELOCITY

# A report should be created in Control-M Console before running the script.
#In this case a report by the name "previous_month_rpt" was created in Control-M console. Where the required feilds in report and period of report etc are configured


ctm=$(command -v ctm 2>/dev/null) || { echo "CTM not found"; exit 1; };
file_location="/tmp/controlm"

if [ $# -eq 0 ];
then
        echo "########### At leat ONE APPLICATION NAME is required to generate the report##############"
        exit 1
fi
for i in $@
do
#date=`date +"%Y%m%d_%H-%M-%S"`
date=`date +"%B%Y"`
echo "{\"filters\":[{\"name\":\"Application\",\"value\":\"${i}\"}]}" > ${file_location}/filter.json
"$ctm" reporting report::get "previous_month_rpt" -o "${file_location}/${i}_jobsReport_${date}.csv" -e rptProd_suresh -f ${file_location}/filter.json
echo "########################################################"
echo "${date} report for the app ${i} generated successfully"
echo "########################################################"
done

##### If you want to use the generate the report which is shared, use the below command
#"$ctm" reporting report::get shared:"Jobs Executions_2" csv -o /home/ctmagent/amba_reports/nadmcde.csv
