#!/bin/bash
#This script will get the details from the other file and formats it and send a mail and clears the file

#Author: Suresh Kumar Nagaram

#send mail alert for the contents available in below file
alert_file=/tmp/alertDetails_filtered.txt
TO="ns0861989@gmail.com"

CC="ns0861989@gmail.com,ns0861989@gmail.com"

if [ ! -s /tmp/alertDetails_filtered.txt ]; then	#If file is empty

        {
#          echo "From: $FROM"
          echo "To: $TO"
          echo "Cc: $CC"
          echo "Subject: NO ABENDS FOUND - Control-M Non-Prod Abend report"
          echo "MIME-Version: 1.0"
          echo "Content-Type: text/plain"
          echo ""
          echo ""
          echo "No jobs were abended in Control-M non-prod since last alert mail."
        } | sendmail -t 2>>/var/log/ctm_mail.err
else

        {
#         echo "From: $FROM"
          echo "To: $TO"
          echo "Cc: $CC"
          echo "Subject: Control-M Non-Prod Abend report"
          echo "MIME-Version: 1.0"
          echo "Content-Type: text/html"
          echo "<!DOCTYPE html>"
		  
		  
          echo "<html>"
          echo "<head>"
          echo "<title>Control-M Alert</title>"
          echo "<style>"
          echo ".header { background-color: #f2f2f2; padding: 10px; text-align: center; }"
          echo ".content { padding: 20px; }"
          echo ".footer { background-color: #f2f2f2; padding: 10px; text-align: center; }"
          echo "body { font-family: Arial, sans-serif; }"
          echo "</style>"
          echo "</head>"
          echo "<body>"
          echo "<div class="header">"
          echo "<h2>Non-Prod CTM Abends</h2>"
          echo "</div>"
          echo "<div class="content">"
          echo "<p>Hello,</p>"
          echo "<p>The following Control-M non-prod jobs were ended abnormally since last alert mail.</p>"
          echo "<style>table, th, td { border:1px solid black; text-align:center; border-collapse:collapse; }</style>"
          echo "<table>"
          echo "<tr>"
          echo "<th>Job Name</th>"
          echo "<th>Application</th>"
          echo "<th>Time</th>"
          echo "<th>Job ID</th>"
          echo "<th>Alert ID</th>"
          echo "<th>Alert Status</th>"
          echo "<th>Alert Message</th>"
          echo "<th>Severity</th>"
          echo "</tr>"

          awk '{
                printf "<tr>"
                printf "<td>%s</td>", $1
                printf "<td>%s</td>", $2
                printf "<td>%s %s %s %s</td>", $3, $4, $5, $6
                printf "<td>%s</td>", $7
                printf "<td>%s</td>", $8
                printf "<td>%s</td>", $9
                printf "<td>%s %s %s</td>", $10, $11, $12
                printf "<td>%s</td>", $13
                printf "</tr>\n"
          }' /tmp/alertDetails_filtered.txt

          echo "</table>"
          echo "<p>Best regards,<br>Control-M Support Team<br>ns0861989@gmail.com</p>"
          echo "</div>"
          echo "</body></html>"
        } | sendmail -t 2>>/var/log/ctm_mail.err
        rc=$?
        if [[ $rc == 0 ]]
        then
                > /tmp/alertDetails_filtered.txt
        fi

fi