'''
This script extracts details mentioned in fieldnames variable from a JSON file which was exported from Control-M planning
This does not take any inputs
File name & its path is defined in this script it self as src_file
The extracted details are written to a CSV file with name defined in dst_file variable in the script
'''
import csv, os, json
from utils.ctm_submodules import extract_event_flow_with_logic, extract_folder_schedule, fix_time_field
from datetime import datetime
timestamp = datetime.now().strftime("%b%Y%d_%H%M%S")
dst_filename = f"extrctd_detls_{timestamp}.csv"
folder = 'C:/Users/sureshkumar.nagaram/Downloads'
src_filename = 'exported_ctm_config_2025Jul30011355.json'
#dst_filename = 'extracted_data.csv'
src_file = os.path.join(folder, src_filename)
dst_file = os.path.join(folder, dst_filename)

# Load JSON file
with open(src_file, 'r') as f:
    data = json.load(f)

# Prepare CSV file
with open(dst_file, 'w', newline='', encoding='utf-8') as csvfile:  #write extracted detailes to the dst_file
    fieldnames = [
        'Application', 'SubApplication', 'RunAs', 'Description', 'JobType', 'FolderName',
        'JobName', 'ResourcePoolKey', 'WeekDays', 'Months', 'MonthDays',
        'ToTime', 'FromTime', 'IncludedCalendars', 'EventsToWaitFor', 'EventsToAdd'
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for folder_name, folder_data in data.items():
        if folder_data.get("Type") != "Folder":
            continue

        sub_application = folder_data.get("SubApplication", "")
        folder_when = folder_data.get("When", {})
        f_fromtime, f_totime, f_weekdays, f_months, f_monthdays, f_included_calendar = extract_folder_schedule(folder_when)
        events_to_wait = extract_event_flow_with_logic(folder_data.get("eventsToWaitFor", {}))
        events_to_add = extract_event_flow_with_logic(folder_data.get("eventsToAdd", {}))

        writer.writerow({
            'Application': folder_data.get("Application", ""),
            'SubApplication': sub_application,
            'JobType': folder_data.get("Type", ""),
            'RunAs': '',
            'Description': folder_data.get("Description", ""),
            'FolderName': folder_name,
            'JobName': '',
            'ResourcePoolKey': '',
            'IncludedCalendars': f_included_calendar,
            'WeekDays': f_weekdays,
            'Months': f_months,
            'MonthDays': f_monthdays,
            'ToTime': f_totime,
            'FromTime': f_fromtime,
            'EventsToWaitFor': events_to_wait,
            'EventsToAdd': events_to_add
        })

        for job_name, job_data in folder_data.items():
            if not isinstance(job_data, dict) or not job_name.isupper():
                continue

            job_type = job_data.get("Type", "")
            run_as = job_data.get("RunAs", "")
            description = job_data.get("Description", "")
            job_when = job_data.get("When", {})
            rule_calndr = job_when.get("RuleBasedCalendars", {})
            included_calendars = rule_calndr.get("Included", [])
            events_to_wait = extract_event_flow_with_logic(job_data.get("eventsToWaitFor", {}))
            events_to_add = extract_event_flow_with_logic(job_data.get("eventsToAdd", {}))


            # Resource Pool key check
            resource_pool_key = ""
            for k, v in job_data.items():
                if isinstance(v, dict) and v.get("Type", "").startswith("Resource:Pool"):
                    resource_pool_key = k
                    break

            # Extract scheduling details
            weekdays = ','.join(job_when.get("WeekDays", []))
            months = ','.join(job_when.get("Months", []))
            monthdays = ','.join(job_when.get("MonthDays", []))
            totime = fix_time_field(job_when.get("ToTime", ""))
            fromtime = fix_time_field(job_when.get("FromTime", ""))

            writer.writerow({
                'Application': job_data.get("Application", ""),
                'SubApplication': job_data.get("SubApplication", ""),
                'JobType': job_type,
                'RunAs': run_as,
                'Description': description,
                'FolderName': folder_name,
                'JobName': job_name,
                'ResourcePoolKey': resource_pool_key,
                'IncludedCalendars': f_included_calendar,
                'WeekDays': weekdays,
                'Months': months,
                'MonthDays': monthdays,
                'ToTime': totime,
                'FromTime': fromtime,
                'EventsToWaitFor': events_to_wait,
                'EventsToAdd': events_to_add
            })