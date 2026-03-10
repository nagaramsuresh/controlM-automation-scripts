'''
This file contains the functions that are required to run the start-controlmJobs-with-jiraWebhooks.py

This requires API URLs of Control-M & Jira
This requires API tokens of Control-M & Jira
This require Jira user's E-Mail ID, by whose name Jira changes should be made

All these sensitive data is stored in .env file and invoked in to this script using os.getenv()
'''
import os, requests, re, html, math
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()

def get_details_from_issue(data):   #Get the details from Jira Webhook request

    issue_key = data.get("key")
    summary = data.get("fields", {}).get("summary")
    description_text = data.get("fields", {}).get("description")
    jira_application = data.get("fields", {}).get("customfield_10033", {}).get("value")
    reporter = data.get("fields", {}).get("reporter", {}).get("displayName")
    ctm_app_name = extract_text(description_text, 'Application:', 'Folder:')
    if ctm_app_name[0] == "MDW":
        env = "PROD"
    elif ctm_app_name[0] == "MDW-DEV":
        env = "DEV"
    else:
        env = "None"
    #env = extract_text(description_text, 'Environment:', 'Folder:')
    ctm_folder_name = extract_text(description_text, 'Folder:')

    return ctm_app_name[0], ctm_folder_name[0], env, issue_key, jira_application, summary, description_text, reporter


def jira_comment_phraser(text): #Format the text for Jira comment
    comment = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
        }
    }
    return comment


JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
USER_EMAIL = os.getenv("USER_EMAIL")
auth = HTTPBasicAuth(USER_EMAIL, JIRA_API_TOKEN)

JIRA_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def update_jira(issue_key, comment, transition_id=None):    #Make a Jira comment and update the ticket status
    comment_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/comment"
    resp_post = requests.post(comment_url, headers=JIRA_HEADERS, json=comment, auth=auth)
    msg = 'Filed to add comment to JIRA'
    if resp_post.status_code != 201:
        return "Failed to add comment to JIRA", resp_post.status_code
    if transition_id:
        transition_url = f"{JIRA_BASE_URL}/rest/api/3/issue/{issue_key}/transitions"
        resp_transition = requests.post(transition_url, headers=JIRA_HEADERS, json={"transition": {"id": transition_id}}, auth=auth)
        if resp_transition.status_code not in (200, 204):
            return f"Transition failed: {resp_transition.text}", resp_transition.status_code
        #return "Comment added & transition successful", resp_transition.status_code

    return "Comment added & transition successful", resp_post.status_code
    '''
    In my environement below are the Transition_ids, which represent the staus of the Jira ticket
    2=Development, 3=QA, 4=UAT, 5=Ready for Production, 6=Complete, 7=Cancelled, 11=To Do/Open, 21=Requirements/In Progress, 31=Waiting for Dev, Returned status code=204 
    '''

def validate_jira_fields(ctm_app_name, ctm_folder_name, jira_application, summary, reporter, ALLOWED_APPLICATIONS=None, ALLOWED_JOBS=None, allowed_reporters=None, allowed_jira_application_names=None):    # Validate the extarcted ticket details against the script rules
    if jira_application not in allowed_jira_application_names:
        return False, f"Invalid Jira application name: {jira_application}"
    if ctm_app_name not in ALLOWED_APPLICATIONS:
        return False, f"Invalid CTM application name: {ctm_app_name}"
    if isinstance(ctm_folder_name, str):
        ctm_folder_name = [ctm_folder_name]
    allowed = ALLOWED_JOBS.get(ctm_app_name, [])
    for f in ctm_folder_name:
        if f not in allowed:
            return False, f"Invalid CTM folder name: {f}"
    if reporter not in allowed_reporters:
        return False, f"Reporter: {reporter} not allowed to create issues"
    return True, (ctm_app_name, ctm_folder_name, jira_application, reporter)

def kick_ctm_job(env, date, folder, job=None):   #Kick Control-M folder/jobs

    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        "x-api-key": ctm_key,
        "Content - Type": "application/json",
        "Accept": "application/json"
    }
    params = {
        "ctm": "IN01",
        "folder": folder,
        "hold": "true",
        "ignoreCriteria": "true",
        "orderDate": date,
        "independentFlow": "true",
        "waitForOrderDate": "false"
    }
    if job:
        params["jobs"] = job

    response = requests.post(f"{ctm_url}/run/order", headers=headers, json=params)
    resp = response.json()
    if response.status_code == 200:
        run_id = resp.get('runId')
        return run_id, response.status_code
    else:
        return resp["errors"][0]["message"], response.status_code

def get_status_with_runid(env, run_id): #Get Control-M folder run status from runid
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        "x-api-key": ctm_key,
        "Content - Type": "application/json",
        "Accept": "application/json"
    }
    statuses = []
    run_status = requests.get(f"{ctm_url}/run/status/{run_id}", headers=headers)
    rsp_json = run_status.json()
    statuses.extend(rsp_json.get("statuses", []))
    folder = [(job.get('name'), job.get('jobId'), job.get('status'), job.get('held'), job.get('type')) for job in statuses if job.get('type') == "Folder"]
    if rsp_json.get("total") > 25:
        total = rsp_json.get("total")
        no_of_pages = math.ceil(total/25)
        for i in range(1, no_of_pages):
            index = 25 * i
            run_status = requests.get(f"{ctm_url}/run/status/{run_id}?startIndex={index}", headers=headers)
            rsp_json = run_status.json()
            statuses.extend(rsp_json.get("statuses", []))
    info = [(job.get('name'), job.get('jobId'), job.get('status'), job.get('held'), job.get('type')) for job in statuses if job.get('type') != "Folder"]
    info.insert(0, folder[0])
    folder_id = info[0][1]
    folder_status = info[0][2]
    return info, folder_id, folder_status




def get_set_with_jobid(jobid, env, order): # Manage jobs with JobID
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        # "x-api-key": sandTkn
        "x-api-key": ctm_key
    }
    post_order = ['kill', 'runNow', 'hold', 'free', 'delete', 'undelete', 'confirm', 'setToOk', 'rerun']
    get_order = ['output', 'log', 'status', 'waitingInfo', 'statistics']
    if order in post_order:
        rsp = requests.post(f"{ctm_url}/run/job/{jobid}/{order}", headers=headers)
        return rsp
    elif order in get_order:
        rsp = requests.get(f"{ctm_url}/run/job/{jobid}/{order}", headers=headers)
        return rsp
    else:
        raise ValueError(f"Unsupported order action: {order}")

def extract_text(text, start_keyword, end_keyword=None):    #extract the text from Jira summary
    # Decode HTML entities like &amp;
    text = html.unescape(text)

    if end_keyword:
        # Extract between two keywords
        #pattern = rf'{re.escape(start_keyword)}(.*?){re.escape(end_keyword)}'
        pattern = rf'{re.escape(start_keyword)}(.*?)(?:{end_keyword})'
        #match = re.search(rf'{re.escape(start_keyword)}(.*?){re.escape(end_keyword)}', text)
    else:
        # Extract from keyword to end of line
        pattern = rf'{re.escape(start_keyword)}(.*)'
        #match = re.search("(?<=start_keyword).*?(?=\n|$)", text)

    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    return [match.strip() for match in matches]