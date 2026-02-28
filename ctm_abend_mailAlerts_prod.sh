#!/bin/bash
# This script is used to process the Control-M Abend data, phrase it and trigger mail & SMS alert

# Set this script while enabling external alerts as described in 
# https://documents.bmc.com/supportu/controlm-saas/en-US/Documentation/Alerts.htm#SettingUpExternalAlerts
#  ctm run alerts:listener:script::set /path/to/ctm_abend_mailAlerts_prod.sh

##Author: Suresh Kumar Nagaram

file_location="${file_location}/controlm"
echo $@ >> ${file_location}/alertRaw.json
# below block of code is from 
# https://github.com/controlm/automation-api-community-solutions/blob/master/helix-control-m/2-external-monitoring-tools-examples/alerts-data-as-variables/alerts_variables.sh

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

ctm=$(command -v ctm 2>/dev/null) || { echo "CTM not found"; exit 1; };

format_date() {
    # Extract substrings and format into "YYYY-MM-DD HH:MM:SS"
    formatted_date="$(echo "$1" | sed -E 's/(.{4})(.{2})(.{2})(.{2})(.{2})(.{2})/\1-\2-\3 \4:\5:\6/')"
    formatted_date="$(date -d "$formatted_date" +"%b %d %Y %H:%M:%S")"
    echo "${formatted_date}"
}

"$ctm" run job:output::get "IN01:${var4}" > ${file_location}/controM_Jobs/output.txt  || true	#get the output file of abend
output="${file_location}/controM_Jobs/output.txt"
"$ctm" run job:log::get "IN01:${var4}" > ${file_location}/controM_Jobs/log.txt || true			#get the log file of abend
log="${file_location}/controM_Jobs/log.txt"

# Define the email components
subject1="Control-M Job Failure Alert"		#Mail subject line for new abend
subject2="Control-M Job Closure Alert"		#Mail subject line for closed abend

## Generate a random boundary for MIME
BOUNDARY="====$(date +%s)===="

# Create the HTML content
html_content2='
<!DOCTYPE html>
<html>
<head>
  <title>Control-M Jb Alert</title>
  <style>
    body { font-family: Arial, sans-serif; }
    .header { background-color: #f2f2f2; padding: 10px; text-align: center; }
    .content { padding: 20px; }
    .footer { background-color: #f2f2f2; padding: 10px; text-align: center; }
  </style>
</head>
<body>
  <div class="header">
    <h1>NEW ALERT</h1>
    <h1>ALERT CLOSED</h1>
  </div>
  <div class="content">
    <p>Hello,</p>
    <p>The following Job has ended abnormally.</p>
    <p>The following failed job alert was closed.</p>
    <style>
table, th, td {
  border: 1px solid black;
  text-align: center;
}
</style>
    <table>
        <tr>
                <th>Job Name</th>
                <th>Application</th>
                <th>Time</th>
                <th>Job ID</th>
                <th>Alert ID</th>
                <th>Alert Status</th>
                <th>Alert Message</th>
                <th>Severity</th>
        </tr>

        <tr>
                <td>'"$var14"'</td>
                <td>'"$var13"'</td>
                <td>'"$(format_date "$var7")"'</td>
                <td>'"$var4"'</td>
                <td>'"$var1"'</td>
                <td>'"$var6"'</td>
                <td>'"$var10"'</td>
                <td>'"$var5"'</td>
        </tr>

    </table>
</br>   Alert was last updated on : '"$(format_date "$var9")"' by '"$var8"'</br></br>Comment:"<b>'"$var20"'</b>"
</br> Please find the attached job output & log files

    <p>Best regards,<br>Control-M Support Team<br>ns0861989@gmail.com</p>
  </div>
  <div class="footer">
    <p><b>Suresh</b></p>
  </div>
</body>
</html>'

html_content1=`sed "/Alert was last updated on/d;/CLOSED/d;/The following failed job alert was closed/d" <<< "$html_content2"`
html_content2=`sed "/NEW/d;/The following Job has ended abnormally/d;/Please find the attached job output/d" <<< "$html_content2"`

case "$var13" in		#Send mail to different ids based on Application name
        "IMF")
                to="ns0861989@gmail.com"
                cc=""
                ;;
        "ABC_EPS_GEN_TXEN")
                to="ns0861989@gmail.com"
                cc=""
                ;;
        *)
                to="ns0861989@gmail.com"
                cc=""
                ;;
esac



# Build the email headers and body

email_body1="To: $to
Cc: $cc
Subject: $subject1
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary=\"$BOUNDARY\"

--$BOUNDARY
Content-Type: text/html; charset=UTF-8
Content-Transfer-Encoding: 7bit

$html_content1
"

# Attach output file with message if file not generated
if [[ -s "$output" ]]; then
    email_body1+="
--$BOUNDARY
Content-Type: application/octet-stream; name=\"$(basename "$output")\"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename=\"$(basename "$output")\"

$(base64 "$output")"
else
    email_body1+="
--$BOUNDARY
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 7bit

Output file was not generated."
fi


# Attach the log file with message if file not generated
if [[ -s "$log" ]]; then
    email_body1+="
--$BOUNDARY
Content-Type: application/octet-stream; name=\"$(basename "$log")\"
Content-Transfer-Encoding: base64
Content-Disposition: attachment; filename=\"$(basename "$log")\"

$(base64 "$log")"
else
    email_body1+="
--$BOUNDARY
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 7bit

Log file was not generated."
fi

email_body2="To: $to
Cc: $cc
Subject: $subject2
MIME-Version: 1.0
Content-Type: text/html

$html_content2"

# Send the email using sendmail
#echo "$email_body" | sendmail -t

#if [[ $var0 == "I" ]]
if [[ "$var0" == "I" && ( "$var10" != "Ended not OK | call App team and inform" && "$var10" != "Ended not OK | Open ticket with App team" ) ]] 	#Trigger mail for only default abends. Filter out the alerts triggered by user defination under Action tab
then
        echo "$email_body1" | sendmail -t
       /usr/bin/python3 sms_script.py $var14 $var13 $var4 $var10 2&>1 >> ${file_location}/controM_Jobs/sms_sent.log		#SMS script to trigger SMS
elif [[ $var6 == "Handled" && ( "$var10" != "Ended not OK | call App team and inform" && "$var10" != "Ended not OK | Open ticket with App team" ) ]]
then
        echo "$email_body2" | sendmail -t
fi