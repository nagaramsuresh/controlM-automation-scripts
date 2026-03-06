'''
Usage:
python export_job_frm_planing.py <folder_name> [job_name]

jobname is optional, if provided it will export the specific job details
folder_name can be '*' to export all folders and jobs with in each folder
else it export the given folder only
'''
import sys, json, os, time
from utils.ctm_submodules import get_ctm_response, get_details_frm_planning_fldr, get_details_frm_planning_job
from datetime import datetime
start = time.perf_counter()
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}") #Print the start time in a human-readable format for better tracking of the script execution duration. This will help in monitoring the performance and identifying any potential bottlenecks in the script.

timestamp = datetime.now().strftime("%b%Y%d_%H%M%S")
dst_filename = f"exported_ctm_config_{timestamp}.json" #Define the filename to be used to save the data

folder = 'C:/Users/sureshkumar.nagaram/OneDrive - AMBA/CTM_plning_export' #Define the folder path/base path to save the exported data

#dst_filename = 'extracted_data.csv'
dst_file = os.path.join(folder, dst_filename)

argments = sys.argv[1:]

if len(argments) == 0:
    print("Folder argument is required.")
    sys.exit(1)

folder = argments[0]
#app_name = argments[1] if len(argments) > 1 else '*' #When used */appName as input for it is not giving stable output as expected. You can try and update this logic as per your requirement.
#job = argments[2] if len(argments) > 2 else None
job = argments[1] if len(argments) > 1 else None
env = 'PROD'

if folder == '*': #all folders from all apps
    srv = 'deployFolder'    #Use ctm deploy folders::get service to get all folder details only, no job details
else:
    srv = 'deploy'  #Use ctm deploy jobs::get service to get specific folder/jobs in detail

params = {
    "server": "IN01",
#    "application": app_name,
    "folder": folder,
    "useArrayFormat": "false"
}

if job:
    params["job"] = job

rsp, sts_code = get_ctm_response(params, env, srv)  # Get job and/or folder details from Control-M planing based on input srv
rsp_json = json.loads(rsp.text)
#print(rsp.text)
if folder == '*':   #if folder is *, get all folders and jobs in each folder and merge the data in a single dictionary to save in a single file. This is to avoid creating multiple files for each folder and job, and to have all the data in a single file for easy reference and analysis. You can change this logic as per your requirement, like saving each folder/job details in separate files if that is more suitable for your use case.
    merged_data = {}
    folder_names = [name for name, value in rsp_json.items() if value.get("Type") == "Folder"]
    #print(folder_names)
    for folder_name in folder_names:
        print(folder_name)
        params["folder"] = folder_name
        rsp, sts_code = get_ctm_response(params, env, 'deploy')  # Get jobs in each folder
        #print(rsp.text)
        rsp_f_json = json.loads(rsp.text)
        merged_data.update(rsp_f_json)
    with open(dst_file, "w") as f:
        json.dump(merged_data, f, indent=4)

elif job:   #This section just prints the job details in STDOUT and can be ignored
    details = get_details_frm_planning_job(rsp_json)  # Get job details from Control-M planing
    print(f"The job '{details["job_name"]}' is using the calander: '{details["j_included_calendars"]}'\n \
                     Scheduled run time is between: {details["j_fromtime"]} and {details["j_totime"]}\n \
                     Scheduled Week days: {details["j_weekdays"]}, Month days: {details["j_months"]}, Months: {details["j_monthdays"]}\n \
                     Waiting on events: {details["j_events_to_wait"]}")
else: #This section just prints the folder details in STDOUT and can be ignored
    details = get_details_frm_planning_fldr(rsp_json)  # Get folder details from Control-M planing
    print(f"The folder '{details["folder_name"]}' is using the calander: '{details["f_included_calendars"]}'\n \
                Scheduled run time is between: {details["f_fromtime"]} and {details["f_totime"]}\n \
                Scheduled Week days: {details["f_weekdays"]}, Month days: {details["f_months"]}, Months: {details["f_monthdays"]}\n \
                Waiting on events: {details["f_events_to_wait"]}")
        
end = time.perf_counter()
print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
elapsed_minutes = (end - start) / 60
print(f"Elapsed: {elapsed_minutes:.2f} minutes")    # prints the total time elapsed
   