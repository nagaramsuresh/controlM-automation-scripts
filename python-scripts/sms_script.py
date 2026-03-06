# Python script to trigger SMS to given mobile number using Twilio
# You may need to install twilio package using the below command
#    python -m pip install --upgrade --no-user twilio   #To install package globally with admin privilages
#	 python -m pip install --upgrade twilio

import sys
sys.path.append('/usr/local/lib/python3.6/site-packages')
from datetime import datetime
from twilio.rest import Client
job = sys.argv[1]
appl = sys.argv[2]
jobid = sys.argv[3]
alert_msg = sys.argv[4] if len(sys.argv) > 4 else "NA"
#dt = datetime.strptime(start_date, "%Y-%m-%d%H:%M:%S.%f")
# Your Account SID and Auth Token from console.twilio.com
account_sid = "ouhihgygon"
auth_token  = "ibiugiughojnugiu"
client = Client(account_sid, auth_token)

current_time = datetime.now().time()
# Define the time ranges for "On site" and "Off shore"
onsite_start = datetime.strptime("11:00", "%H:%M").time()	#Alert onsite team from 11:00:00
onsite_end = datetime.strptime("20:30", "%H:%M").time()		#Alert onsite team until 20:30:00

    # Determine if it's On site or Off shore
if onsite_start <= current_time < onsite_end:
    numbers_to_message = ['+11234567890','+11234567890']	#Onsite team members mobile numbers
else:
    numbers_to_message = ['+11234567890','+11234567890']	#Offshore team members mobile numbers
#from_='From number to be used'
for number in numbers_to_message:
    client.messages.create(
            body=f'Control-M job failure alert:\nJob: {job}\nJobID: {jobid}\nApp: {appl}\nAdditional Details sent to: ns0861989@gmail.com',
        from_='+11234567890',
        to=number
    )
print(f"SMS sent to {number}")