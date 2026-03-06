from datetime import date, datetime, timedelta
import requests, re, html, os, sys, json, shutil, math
from dotenv import load_dotenv
load_dotenv()

def get_date_yymmdd(ipDate):    # Get date in YYMMDD format
    if isinstance(ipDate, (date, datetime)):
        return ipDate.strftime('%y%m%d')
    return None

def get_date_pretty(ipDate):    # Get date in Month Day Year Hour:Minute:Second format
    dt = datetime.strptime(ipDate, '%Y%m%d%H%M%S')
    if isinstance(dt, (date, datetime)):
        return dt.strftime('%b %d %Y %H:%M:%S')
    return None

def get_date_insec(ipDate): # Get date in seconds
    dt = datetime.strptime(ipDate, '%Y%m%d%H%M%S')
    if isinstance(dt, (date, datetime)):
        return int(dt.timestamp())
    return None

def get_date_crntmin(ipDate): # Get current time in minutes
    if isinstance(ipDate, (date, datetime)):
        hrs = int(ipDate.strftime('%H'))
        mns = int(ipDate.strftime('%M'))
        mins = hrs*60 + mns
        return mins
    return None


def get_ctm_response(params, env, srv):   #get job statuses

    # Build the variable name dynamically
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        # "x-api-key": sandTkn
        "x-api-key": ctm_key
    }
    if srv == 'run':    #run service
        rsp = requests.get(f"{ctm_url}/run/jobs/status", headers=headers, params=params)
    elif srv == 'deploy':   #get specific folder/jobs in detail
        #Ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm#run17
        rsp = requests.get(f"{ctm_url}/deploy/jobs", headers=headers, params=params)
        #ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_DeployService.htm#deploy3
    elif srv == 'deployFolder':  #get all folder details only, no job details
        #ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_DeployService.htm#deploy8
        rsp = requests.get(f"{ctm_url}/deploy/folders", headers=headers, params=params)
    #return rsp
    if rsp.status_code != 200:
        return rsp.json().get("errors", [{}])[0].get("message", "No message found"), rsp.status_code
    else:
        return rsp, rsp.status_code


def get_set_with_jobid(jobid, env, order): # Manage jobrelated tasks with JobID (tasks are mentioned in post_order and get_order lists)
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
    #Ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm#JobManagement
    if order in post_order:
        rsp = requests.post(f"{ctm_url}/run/job/{jobid}/{order}", headers=headers)
        return rsp
    elif order in get_order:
        rsp = requests.get(f"{ctm_url}/run/job/{jobid}/{order}", headers=headers)
        return rsp
    else:
        raise ValueError(f"Unsupported order action: {order}")

def get_exe_status_jobid(jobid, env): # Get jobs execution status
    #Ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm#run4
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        # "x-api-key": sandTkn
        "x-api-key": ctm_key
    }
    rsp = requests.get(f"{ctm_url}/run/job/{jobid}/status", headers=headers)
    rsp_json = rsp.json()
    run_status = rsp_json.get("status")
    return run_status

def kick_ctm_job(env, date, folder, job=None):   #Kick folder/jobs
    #Ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm#run5
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        # "x-api-key": sandTkn
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

def get_status_with_runid(env, run_id): #Get the status of folder and/or jobs with runID. Ref: https://documents.bmc.com/supportu/API/Monthly/en-US/Documentation/API_Services_RunService.htm#run51
    url = f"CTM_{env}_API_BASE"
    ctm_url = os.getenv(url)
    key = f"CTM_{env}_API_KEY"
    ctm_key = os.getenv(key)
    headers = {
        # "x-api-key": sandTkn
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


def get_pool_name(waitDetails): #get Resource pool name from wait details if it is waiting on resource
    match = re.search(r"(?<=The Job is waiting for resource ).*?(?=, Quantity)", waitDetails)
    if match:
        result = match.group(0)
        #print(result)  # ➜ ABC_XYZ
        return result
    else:
        return None

def get_wait_events(waitDetails):   #get events name from wait details if it is waiting on event
    match = re.search(r"(?<=The Job is dependant on condition ).*?(?=_OK|$)", waitDetails)
    #match = re.search(r'The Job is dependant on condition ([\w\-]+(?:_[\w\-]+)*?)(?:_OK)?(?="|\]|\s|$)', waitDetails)
    if match:
        result = match.group(0)
        #print(result)
        return result
    else:
        return None

def extract_text(text, start_keyword, end_keyword=None): # Extract text between two keywords or from a keyword to the end of line
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


def get_application(args): # Get application name from input argument and validate it against the list of supported applications
    if not args:
        print("No input provided.")
        sys.exit(1)

#    arg = args[0].lower()  # Only use first argument, case-insensitive

    match args:
        case 'imf':
            return 'IMF'
        case 'eps':
            return 'ABC_EPS_GEN_TXEN'
        case 'fin':
            return 'FINSYS'
        case 'ctm':
            return 'CTM'
        case 'maaes':
            return 'MAAES'
        case 'macwdb':
            return 'MACWDB'
        case 'madoc':
            return 'MADOC'
        case 'mags':
            return 'MAGS_ISIS_IBA_A2A'
        case 'wbn':
            return 'MAGS_ISIS_WBN'
        case 'mavel':
            return 'MAVEL'
        case 'mevel':
            return 'MEVEL'
        case 'mdw':
            return 'MDW'
        case 'mercator':
            return 'MERCATOR'
        case 'pl':
            return 'PLCOM'
        case 'urb':
            return 'URB_UserDaily'
        case 'us1530':
            return 'US1530_UserDaily'
        case 'us':
            return 'US_UserDaily'
        case _:
            print(f"Invalid Input. Please provide a valid application name. Given app '{args}' does not exist.")
            sys.exit(1)


def get_nearest_timestamp(timestamps):  #Get the nearest timestamp to current time from a list of timestamps in 'yyyymmddhhmmss' format for a cyclic job/folder which has multiple timestamps for each day based on the frequency of the cycle.
    """
    Given a list of timestamps in 'yyyymmddhhmmss' format,
    return the one closest to current time.
    """
    now = datetime.now()
    # Convert to datetime objects
    timestamp_objs = [datetime.strptime(ts, "%Y%m%d%H%M%S") for ts in timestamps]
    # Find nearest to now
    closest = min(timestamp_objs, key=lambda dt: abs(dt - now))
    # Return in original format
    return closest.strftime("%Y%m%d%H%M%S")

def get_statistics(rspjson, jobid, job): #get job/folder runtime statistics, to get average runtime of the job/folder and compare it with current runtime to predict if the job/folder is likely to breach SLA
    rsp_statuses = rspjson.get("statuses", [])
    if job:
        start_time = next((job.get("startTime") for job in rsp_statuses if job.get("status") == "Executing" and job.get("type") != "Folder"), None)
    else:
        start_time = next((job.get("startTime") for job in rsp_statuses if job.get("status") == "Executing" and job.get("type") == "Folder"), None)
    pool_strt_time = datetime.strptime(start_time, "%Y%m%d%H%M%S")
    now_time = datetime.now()
    elapsed_time = str(now_time - pool_strt_time).split('.')[0]
    stat = get_set_with_jobid(jobid, 'PROD', 'statistics') # get statistics of the job with jobID
    stat_json = json.loads(stat.text)
    stat_time = stat_json.get('periods')[0].get('runInfo').get('averageInfo').get('runTime')    
    return start_time, elapsed_time, stat_time

def get_objs(rspjson):  #get Folder ID and count of jobs in the folder from the input JSON
    cont =  rspjson.get("returned")
    statuses = rspjson.get("statuses", [])
    #length = sum(1 for job in statuses if job.get("type") in ["Job", "Command"])
    length = sum(1 for job in statuses if job.get("type") != "Folder")
    folderid = [job.get("jobId") for job in statuses if job.get("type") == "Folder"]
    return cont, statuses, length, folderid

def get_obj_folderName(statuses, folderid): #get folder name with folder ID from the list of statuses
    foldername = next((job.get("name") for job in statuses if job.get("type") == "Folder" and job.get("jobId") == folderid), None)
    return foldername
def get_obj_jobname(statuses, jobid): #get Job name & current start time with job ID from the list of statuses. If the job has multiple start times for each day based on the frequency of the cycle, get the nearest start time to current time.
    jobname = next((job.get("name") for job in statuses if job.get("type") in ["Job", "Command"] and job.get("jobId") == jobid), None)
    crnttime = next((job.get("estimatedStartTime") for job in statuses if job.get("type") in ["Job", "Command"] and job.get("jobId") == jobid), None)
    statrtime = next((job.get("startTime") for job in statuses if job.get("type") in ["Job", "Command"] and job.get("jobId") == jobid), None)
    if isinstance(crnttime, list):
        first_time = crnttime[0] if crnttime else None
    elif isinstance(crnttime, str) and crnttime:
        first_time = crnttime
    else:
        first_time = crnttime
    if first_time:
        crnttime = first_time
    else:
        crnttime = statrtime


    return jobname, [crnttime]


def get_onDemandJob(statuses, jobid, bkpcont, appl, rundate, base_path): #get job details which are not available in the reference file exported from viewpoint and update the reference JSON file with those details for the on-demand job which is not part of the regular cycle and hence does not have details in the reference file. This is to ensure that the on-demand job details are also captured for future reference and analysis.
    odjob = next((job for job in statuses if job.get("jobId") == jobid), None)
    print("This is On-demand job", jobid)
    print(f'{base_path}{appl}jobs{rundate}.json, {base_path}{appl}jobs{rundate}_bkp{bkpcont}_{jobid}.json')
    shutil.copy2(rf'{base_path}{appl}jobs{rundate}.json', rf'{base_path}{appl}jobs{rundate}_bkp{bkpcont}_{jobid}.json')

    with open(rf'{base_path}{appl}jobs{rundate}.json', "r+") as f:
        try:
            existing_data = json.load(f)
            # Ensure it's a dictionary with a 'statuses' list
            if isinstance(existing_data, dict) and "statuses" in existing_data:
                existing_data["statuses"].append(odjob)
            else:
                # If the structure is not as expected, create a new one
                existing_data = {
                    "returned": 1,
                    "statuses": [odjob],
                    "total": 1
                }

        except json.decoder.JSONDecodeError:
            # If file is empty or invalid JSON
            existing_data = {
                "returned": 1,
                "statuses": [odjob],
                "total": 1
            }
        existing_data["returned"] = len(existing_data["statuses"])
        existing_data["total"] = len(existing_data["statuses"])
        f.seek(0)
        json.dump(existing_data, f, ensure_ascii=False, indent=4)
        f.truncate()
    return odjob

def get_statuses_from_file(path): # get job/folder statuses from the reference JSON file exported from viewpoint based on the input path. This refernce file is exported on application's new day. right after all jobs for that load in to schedule
    with open(rf"{path}", "r") as f:
        rsp = json.load(f)
    return rsp

def get_rundate(appl):  # Get run date based on the application and current time. For IMF application, if current time is greater than 930 min (15:30), consider run date as today, else consider yesterday as run date. For other applications, if current time is greater than 420 min (07:00), consider run date as today, else consider yesterday as run date. 930 min & 420 min are number of minutes from 00:00 to 15:30 and 07:00 respectively.
    tday = datetime.today().date()
    ystrday = tday - timedelta(days=1)

    today = get_date_yymmdd(tday)
    yesterday = get_date_yymmdd(ystrday)
    crntmin = get_date_crntmin(datetime.now())
    if appl == 'IMF':
        rundate = today if crntmin > 930 else yesterday
    else:
        rundate = today if crntmin > 420 else yesterday
    print(f"\n################ Application is {appl} & Run Date is {rundate} ###############\n")
    return rundate

def extract_event_flow_with_logic(section): #Get all event references from eventsToWaitFor/eventsToAdd block, preserving logical operators like 'OR', 'AND', '(', ')', and return a comma-separated string representing the event logic.
    """
    Extracts all event references from an eventsToWaitFor/eventsToAdd block,
    preserving logical operators like 'OR', 'AND', '(', ')'.
    Returns a comma-separated string representing the event logic.
    """
    if not isinstance(section, dict):
        return ""

    def flatten_events(events):
        result = []
        for evt in events:
            if isinstance(evt, dict) and "Event" in evt:
                result.append(evt["Event"])
            elif isinstance(evt, str):
                result.append(evt)
            elif isinstance(evt, list):
                # Recursively flatten nested lists
                result.extend(flatten_events(evt))
        return result

    events = section.get("Events", [])
    flattened = flatten_events(events)
    return ','.join(flattened)

def fix_time_field(time_val):   #add ' infront of time, so that it is properly formatted. ex: '0530
    """
    Returns a time string padded with zeros if it's numeric.
    Leaves symbolic values (like '>') untouched.
    """
    if isinstance(time_val, int):
        return f"'{time_val:04d}"
    if isinstance(time_val, str):
        if time_val.isdigit():
            return f"'{time_val.zfill(4)}"
        return time_val
    return ""

def extract_folder_schedule(when_obj):  # Extracts scheduling details from a folder's "When" object.
    from_time = fix_time_field(when_obj.get("FromTime", ""))
    to_time = fix_time_field(when_obj.get("ToTime", ""))
    weekdays, months, monthdays, included_calendars = [], [], [], []

    rule_cal = when_obj.get("RuleBasedCalendars", {})
    included_calendars = rule_cal.get("Included", [])
    for cal_name, cal_data in rule_cal.items():
        if isinstance(cal_data, dict) and "When" in cal_data:
            when = cal_data["When"]
            weekdays.extend(when.get("WeekDays", []))
            months.extend(when.get("Months", []))
            monthdays.extend(when.get("MonthDays", []))

    return from_time, to_time, ','.join(weekdays), ','.join(months), ','.join(monthdays), ','.join(included_calendars)

def get_details_frm_planning_fldr(data): # Extracts folder details from Control-M planning data.#   
    for folder_name, folder_data in data.items():
        if folder_data.get("Type") != "Folder":
            continue

        application =folder_data.get("Application", "")
        sub_application = folder_data.get("SubApplication", "")
        f_description = folder_data.get("Description", "")
        f_type = folder_data.get("Type", "")
        folder_when = folder_data.get("When", {})
        f_fromtime, f_totime, f_weekdays, f_months, f_monthdays, f_included_calendars = extract_folder_schedule(folder_when)
        events_to_wait = extract_event_flow_with_logic(folder_data.get("eventsToWaitFor", {}))
        events_to_add = extract_event_flow_with_logic(folder_data.get("eventsToAdd", {}))
    return {
        'application': application,
        'sub_application': sub_application,
        'f_description': f_description,
        'folder_name': folder_name,
        'f_type': f_type,
        'f_fromtime': f_fromtime,
        'f_totime': f_totime,
        'f_weekdays': f_weekdays,
        'f_months': f_months,
        'f_monthdays': f_monthdays,
        'f_included_calendars': f_included_calendars,
        'f_events_to_wait': events_to_wait,
        'f_events_to_add': events_to_add
    }

def get_details_frm_planning_job(data): # Extracts job details from Control-M planning data.#
    for job_name, job_data in data.items():
            if not isinstance(job_data, dict) or not job_data.get("Type", "").startswith("Job"):
                continue
            application = job_data.get("Application", "")
            sub_application = job_data.get("SubApplication", "")
            j_type = job_data.get("Type", "")
            run_as = job_data.get("RunAs", "")
            j_description = job_data.get("Description", "")
            job_when = job_data.get("When", {})
            j_rule_calndr = job_when.get("RuleBasedCalendars", {})
            j_included_calendars = j_rule_calndr.get("Included", [])
            j_events_to_wait = extract_event_flow_with_logic(job_data.get("eventsToWaitFor", {}))
            j_events_to_add = extract_event_flow_with_logic(job_data.get("eventsToAdd", {}))
            j_weekdays = ','.join(job_when.get("WeekDays", []))
            j_months = ','.join(job_when.get("Months", []))
            j_monthdays = ','.join(job_when.get("MonthDays", []))
            j_totime = fix_time_field(job_when.get("ToTime", ""))
            j_fromtime = fix_time_field(job_when.get("FromTime", ""))
    return {
        'application': application,
        'sub_application': sub_application,
        'j_type': j_type,
        'run_as': run_as,
        'j_rule_calndr': j_rule_calndr,
        'j_included_calendars': j_included_calendars,
        'j_weekdays': j_weekdays,
        'j_months': j_months,
        'j_monthdays': j_monthdays,
        'j_totime': j_totime,
        'j_fromtime': j_fromtime,
        'j_events_to_wait': j_events_to_wait,
        'j_events_to_add': j_events_to_add,
        'job_name': job_name,
        'j_description': j_description
    }
def get_details_frm_planning(data): # Extracts folder/job details from Control-M planning data.#   
    for folder_name, folder_data in data.items():
        if folder_data.get("Type") != "Folder":
            continue

        application =folder_data.get("Application", "")
        sub_application = folder_data.get("SubApplication", "")
        f_description = folder_data.get("Description", "")
        f_type = folder_data.get("Type", "")
        folder_when = folder_data.get("When", {})
        f_fromtime, f_totime, f_weekdays, f_months, f_monthdays, f_included_calendars = extract_folder_schedule(folder_when)
        events_to_wait = extract_event_flow_with_logic(folder_data.get("eventsToWaitFor", {}))
        events_to_add = extract_event_flow_with_logic(folder_data.get("eventsToAdd", {}))
        for job_name, job_data in folder_data.items():
            if not isinstance(job_data, dict) or not job_data.get("Type", "").startswith("Job"):
                continue
            application =job_data.get("Application", "")
            sub_application = job_data.get("SubApplication", "")
            j_type = job_data.get("Type", "")
            run_as = job_data.get("RunAs", "")
            j_description = job_data.get("Description", "")
            job_when = job_data.get("When", {})
            j_rule_calndr = job_when.get("RuleBasedCalendars", {})
            j_included_calendars = j_rule_calndr.get("Included", [])
            j_events_to_wait = extract_event_flow_with_logic(job_data.get("eventsToWaitFor", {}))
            j_events_to_add = extract_event_flow_with_logic(job_data.get("eventsToAdd", {}))
            j_weekdays = ','.join(job_when.get("WeekDays", []))
            j_months = ','.join(job_when.get("Months", []))
            j_monthdays = ','.join(job_when.get("MonthDays", []))
            j_totime = fix_time_field(job_when.get("ToTime", ""))
            j_fromtime = fix_time_field(job_when.get("FromTime", ""))
    return {
        'application': application,
        'sub_application': sub_application,
        'folder_name': folder_name,
        'f_description': f_description,
        'f_type': f_type,
        'f_fromtime': f_fromtime,
        'f_totime': f_totime,
        'f_weekdays': f_weekdays,
        'f_months': f_months,
        'f_monthdays': f_monthdays,
        'f_included_calendars': f_included_calendars,
        'f_events_to_wait': events_to_wait,
        'f_events_to_add': events_to_add,
        'j_type': j_type,
        'run_as': run_as,
        'j_rule_calndr': j_rule_calndr,
        'j_included_calendars': j_included_calendars,
        'j_weekdays': j_weekdays,
        'j_months': j_months,
        'j_monthdays': j_monthdays,
        'j_totime': j_totime,
        'j_fromtime': j_fromtime,
        'j_events_to_wait': j_events_to_wait,
        'j_events_to_add': j_events_to_add,
        'job_name': job_name,
        'j_description': j_description
    }
    