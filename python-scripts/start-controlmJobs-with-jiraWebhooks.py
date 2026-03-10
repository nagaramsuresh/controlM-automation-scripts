'''
##################################################################################
# This script must run continuously so it can listen for incoming Jira Webhooks. #
##################################################################################

Starting the script:  python start-controlmJobs-with-jiraWebhooks.py

##############################
#   Purpose of the script    #
##############################

The script is used to trigger on-demand Control-M jobs, whenever a Jira ticket is created containing the Control-M application name and folder details.
The script is invoked through a Jira Webhook.
The Webhook is triggered after a Jira ticket is created and validated using Jira Automation rules.

The script can handle multiple requests simultaneously, meaning multiple Jira tickets can be created and approved at the same time.

##############################
#   Jira Automation Rules    #
##############################

Two Jira automation rules have been configured to ensure the Webhook triggers this backend script.

   Rule 1 - Notification Rule
    1. This rule sends an email alert to stakeholders indicating that a Control‑M request has been raised.
        This rule succeeds when all the following conditions are met:
                A new Jira item is created.
                The Jira application field is set to Control-M.
                The reporter (ticket creator) is one of the allowed users.
                The Jira Summary contains the keyword “Please kick MDW folders”.
                The application mentioned in the Summary is either MDW or MDW‑DEV

      After the notification email is received, an authorized user assigns the Jira ticket to a specific person.
      This assignment acts as an approval step, which triggers Rule 2.
       
   Rule 2 – Webhook Trigger Rule
    2. This rule triggers the Webhook that starts the backend Python script.
        This rule succeeds when all the following conditions are satisfied:
                When a work item is assigned to a user.
                When the above assignment is made by specific set of users given(User condition, Initiator is)
                When the reporter is from a given set of users (Reporter is who created the Jira)
                When the Jira assigned user matches (Assignee is)
                When Jira application matches
                When SUmmery contains a specific keyword
                When the Jira status is Open
            
          When these conditions are met, the Webhook (e.g., https://xyz.com/jira-webhook) is triggered.
            If the Webhook receives a 200 response from the backend host running the script, a success email notification is sent.

#######################################
#   Webhook Handling on Apache HTTPD  #
#######################################
            
The https://xyz.com/jira-webhook request is served by an Apache HTTPD server.
The script path and other routing details are configured inside a VirtualHost block as shown below.
    
   Note: mod_proxy and mod_proxy_http must be enabled in the main HTTPD configuration.
        <VirtualHost *:8087> #8087 here is the post on which httpd is listining

            # Log the requests
            CustomLog /var/log/webhook_access.log combined
            ErrorLog /var/log/webhook_error.log

            # Proxy requests to your Python script running Flask on port 5000
            ProxyPreserveHost On
           # ProxyPass /jira-webhook http://hostname.com:8188/jira-webhook
           # ProxyPassReverse /jira-webhook http://hostname.com:8188/jira-webhook
            ProxyPass /jira-webhook http://hostname.com:8188/jira-webhook
            ProxyPassReverse /jira-webhook http://hostname.com:8188/jira-webhook
        </VirtualHost>


'''

from flask import Flask, request, jsonify
import logging, time, sys, os, json, traceback
from multiprocessing import Process
from datetime import datetime

# Import your custom modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from utils.jira-webhook-submodules import *

# Validated fields (your original config)
allowed_reporters = {"Suresh Kumar", " Sarath", "Reddy", "Praveen"} #Script will continue only if this list of users created the Jira
ALLOWED_APPLICATIONS = {"MDW-DEV", "MDW"}   #Script will continue only if these applications are mentioned in Jira description
ALLOWED_JOBS = {
    "MDW-DEV": ["SYSWV#auto-mdw-folder", "SYSWV#auto-mdw-folder1", "SYSWV#auto-mdw-folder2", "SYSWV#MDWRQ6X-test", "SYSWV#MDWRQ6X_DEV", "SYSWV#NMDWRQ10_DEV", "SYSWV#MDWRQ11X_DEV", "SYSWV#NMDWRQ12_DEV", "SYSWV#MDWRQ14X_DEV", "SYSWV#MDWRQ6X_SQL_DEV", "SYSWV#NMDWRQ10_SQL_DEV", "SYSWV#MDWRQ11X_SQL_DEV", "SYSWV#NMDWRQ12_SQL_DEV", "SYSWV#MDWRQ14X_SQL_DEV"],
    "MDW": ["SYSWV#MDWRQ6X", "SYSWV#NMDWRQ10", "SYSWV#MDWRQ11X", "SYSWV#NMDWRQ12", "SYSWV#MDWRQ14X", "SYSWV#MDWDMALU", "SYSWV#MDWRQ6X_SQL", "SYSWV#NMDWRQ10_SQL", "SYSWV#MDWRQ11X_SQL", "SYSWV#NMDWRQ12_SQL", "SYSWV#MDWRQ14X_SQL", "SYSWV#MDWDMALU_SQL"]
}   #Script will continue only if these list of folders are mentioned in Jira description
allowed_jira_application_names = {"Control-M"}  #Script will continue only if these application name categorie is selected in Jira

app = Flask(__name__)

# Main Flask logger (NOT workflow logs)
logging.basicConfig(
    filename='/tmp/jira-logs/jira_webhook.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =========================================================================================
#  WEBHOOK: Spawns a NEW PROCESS per request (full isolation)
# =========================================================================================
@app.route('/jira-webhook', methods=['POST'])   #/jira-webhook is the URI configured in Jira webhook
def jira_webhook():
    raw = request.data.decode("utf-8", errors="replace")
    logging.info("Received webhook")

    try:
        safe = raw.replace("\r", "\\r").replace("\n", "\\n")
        data = json.loads(safe)
    except:
        logging.error("Invalid JSON")
        return "invalid json", 400

    # Start workflow as a new process
    p = Process(target=workflow_processor, args=(data,))
    p.start()

    logging.info("Workflow spawned as PID=%s", p.pid)
    return jsonify({"status": "started", "pid": p.pid}), 200


# =========================================================================================
#   WORKFLOW PROCESS (FULL INDEPENDENT PIPELINE)
# =========================================================================================
def workflow_processor(data):
    # Set per-process logfile
    ctm_app, ctm_folders, env, issue_key, jira_app, summary, desc, reporter = get_details_from_issue(data)  #Get the feilds from Jira webhook data
    pid = os.getpid()
    log_dir = "/tmp/jira-logs"
    os.makedirs(log_dir, exist_ok=True)

    log_file = f"{log_dir}/workflow_{issue_key}_{pid}.log"  #logging.info/error will be printed in this file

    # Configure logging ONLY for this process
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        force=True
    )

    logging.info("=== Workflow Started ===")
    logging.info("PID: %s", pid)
    logging.info("Issue: %s", issue_key)

    try:
        # Extract main fields
        ctm_app, ctm_folders, env, issue_key, jira_app, summary, desc, reporter = get_details_from_issue(data)  #Get the feilds from Jira webhook data


        folders = [f.strip() for f in ctm_folders.split(",")]   #get list of folders from Jira description

        # Validate data
        valid, validated = validate_jira_fields(ctm_app, folders, jira_app, summary, reporter, ALLOWED_APPLICATIONS, ALLOWED_JOBS, allowed_reporters, allowed_jira_application_names)   #Valildate the feilds extracted from Jira issue

        if not valid:   #Exit if all validations are not met
            msg = jira_comment_phraser(f"Issue validation failed: {validated}")
            update_jira(issue_key, msg, 21)
            logging.error("status: Jira validation FAILED, Reason: %s", validated)
            return

        ctm_app, folders, jira_app, reporter = validated    #Continue if Jira feilds are validated
        logging.info("Validated feilds are: Jira Application: %s, Summary: %s, CTM-Application: %s, Folder: %s, Environment: %s, Requestor: %s", jira_app, summary, ctm_app, folders, env, reporter)
        logging.info("Issue: %s, Jira Application: %s, Summary: %s, CTM-Application: %s, Folder: %s, Environment: %s, Requestor: %s", issue_key, jira_app, summary, ctm_app, folders, env, reporter)

        run_ids = []

        # ================================================================
        # 1. KICK ALL FOLDERS
        # ================================================================
        comment = ''
        for f in folders:   #Kick all folders mentioned in Jira description one after other and note runid
            runid, rc = kick_ctm_job(env, "current", f)

            if rc != 200:
                logging.error("Control-M folder %s kick failed with code %s, run_id=%s", f, rc, runid)
                return

            run_ids.append(runid)

            info, folderid, status = get_status_with_runid(env, runid) #get FIlder details from runid
            get_set_with_jobid(folderid, env, 'free')   #Unhold the folder
            get_set_with_jobid(folderid, env, 'confirm')    #Confirm the folders which are waiting for user confirmation. If the folder is  not waiting on user confirmation, script will ignore the error
            time.sleep(10)  #Wait for 10Sec so that folder gets unheld & confirmed
            rsp = get_set_with_jobid(folderid, env, 'status')   #get the status of the folder
            rsp_json = rsp.json()
            status = rsp_json.get("status")
            logging.info("Folder %s (%s) is kicked and its status is '%s'...", f, folderid, status) #Log the folder status
            comment += f'Folder {f} ({folderid}) is kicked and its status is "{status}"...\n'   #Develop Jira comment

        #jira_comment = jira_comment_phraser(f'{comment}')
        msg, status = update_jira(issue_key, jira_comment_phraser(comment), 2) #2=Development   #Make a Jira comment after all folder in description are kicked
        if status != 201: #201 is success code from JIRA
            logging.error("Updating jira after job kick failed with code %s, message=%s", status, msg)
            return #Script is struck at this point with return statement

        comment = ''
        # ================================================================
        # 2. MONITOR EACH FOLDER UNTIL “Ended OK”
        # ================================================================
        for runid in run_ids:

            while True:  # Loop until folder ends OK

                info, folderid, folder_status = get_status_with_runid(env, runid)
                folder_name = info[0][0]

                # Folder ended OK → exit while
                if folder_status == "Ended OK":
                    break

                # ---------------------------------------------------------
                #  CHECK JOBS STRICTLY IN ORDER
                # ---------------------------------------------------------
                first_failure = None

                for job in info[1:]:
                    job_name, jobid, status, held, typ = job

                    if status == "Ended Not OK":
                        first_failure = (job_name, jobid, status)
                        break
                    elif status == "Executing":
                        first_failure = (job_name, jobid, status)
                        break

                # If no failure found but folder not ended → just wait
                if not first_failure:
                    logging.info("Folder: %s (%s) is still '%s', due to one or more jobs in wait state'. \n Waiting for job to 'END OK'...", folder_name, folderid, folder_status)
                    time.sleep(10)  Wait 10Sec
                    continue

                # ---------------------------------------------------------
                # A FAILED JOB WAS FOUND
                # ---------------------------------------------------------
                job_name, jobid, job_status = first_failure
                comment = f'Folder {folder_name} ({folderid}) is still "{folder_status}",  due to the Job {job_name} ({jobid}) is "{status}".\n Waiting for job to "END OK"...'
                logging.info("Folder: %s (%s) is still '%s', due to the job %s (%s) is '%s'. \n Waiting for job to 'END OK'...", folder_name, folderid, folder_status, job_name, jobid, status)
                if job_status == 'Ended Not OK':
                    msg, rc = update_jira(issue_key, jira_comment_phraser(comment), 21) #If job fails, make Jira comment and change Jira status to Requirements
                else:
                    msg, rc = update_jira(issue_key, jira_comment_phraser(comment), 2) #
                comment = ''
                if rc != 201:
                    logging.error("Updating jira failed for failed job %s details with code %s, message=%s", job_name, job_status, msg)
                    time.sleep(60)
                    continue

                #logging.info("Failure: Folder %s (%s) → waiting 5 minutes", job_name, jobid)
                time.sleep(300)  # 5 minutes Wait for 5Min after all jobs in folder are scanned for Ended Not OK

            # Ended OK
            logging.info("Folder %s (%s) executed successfully with status ***%s***", folder_name, folderid, folder_status)
            comment += f'Folder {folder_name} ({folderid}) executed successfully with status: **{folder_status}**\n'
        #comment = jira_comment_phraser(f"{comment}")
        msg, status = update_jira(issue_key, jira_comment_phraser(comment), 6) #Comment jira and mark completed

        logging.info("=== Workflow completed for %s ===", issue_key)

    except Exception as e: 
        error = f"Fatal workflow error: {str(e)}\n{traceback.format_exc()}"
        logging.error(error)
        update_jira(issue_key, jira_comment_phraser(error), 31)


# =========================================================================================
#  MAIN
# =========================================================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8188, debug=False) #Start a Flask process listining on port 8188. Port can be user defined
    #app.run(host='0.0.0.0', port=443, ssl_context=('cert.pem', 'key.pem')) #HTTPS listining port