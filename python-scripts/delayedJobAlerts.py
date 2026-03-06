''' 
This python script is designed to monitor Control-M jobs for a specified 
    application and run date, identify any non-cyclic jobs that are delayed beyond 
    a certain threshold from their scheduled start time, and send email alerts with details
    about the delayed jobs, including their wait status and any resources or events 
    they are waiting on. The script retrieves the currunt job statuses from Control-M,
    compares current start times with scheduled start times, which was exported when new schedule is loaded,
    and gathers additional information about wait conditions and resource usage
    to provide comprehensive alert notifications.
    
 Usage: 
 python delayedJobAlerts.py <application> <application>
This script requires at least one application name as a command-line argument. 
example: python delayedJobAlerts.py eps imf
example: python delayedJobAlerts.py eps
'''
import sys, pdb #pdb is used for debugging, you can set breakpoints in the code to inspect variables and flow during execution
import time
from utils.ctm_submodules import *
from utils.send_mail import send_mail
from colorama import Fore, Style, init  # Initialize colorama for colored stdout print
init(autoreset=True)
#print(Fore.RED + "This is RED text")

def main():

    argmts = sys.argv[1:]
    arg_cnt = len(argmts)
    env = 'PROD' # Define environment as PROD, you can change it to DEV or any other environment as per your requirement. Make sure to have the necessary access and permissions to retrieve job details from the specified environment.
    
    if arg_cnt == 0:
        print("Error: Please provide at least one application name as an argument.")
        sys.exit(1)
    for argmnts in argmts:
        bkpcont = 1     # viewpoint copy during Ondemand jobs
        threshold = 1800  # delay threshold in seconds to trigger alert, you can change this value as per your requirement. Currently, it is set to 1800 seconds (30 minutes).
        appl = get_application(argmnts) #Get full application name from the short input argument
        rundate = get_rundate(appl) #Get run date based on the application and current time.

        base_path = r'C:/Users/sureshkumar.nagaram/Downloads/ctm' #Define base path to store the reference files exported from viewpoint and other details. Make sure this path has necessary read/write permissions and enough storage space for the files. You can change this path as per your requirement.
        #base_path = r'/tmp/controM_Jobs'

        ref_file_path = rf'{base_path}/{appl}jobs{rundate}.json' #This is the referrence file exported from the view point right after new schedule is loaded
        params = {
            "application": appl,
            "status": "Wait User,Wait Resource,Wait Host,Wait Workload,Wait Condition",
            "orderDateTo": rundate
        }
        rsp, sts_code = get_ctm_response(params, env, 'run')   # get current list of jobs  that are waiting along with their details with run service

        with open(rf"{base_path}/{appl}currentWaitList.json", "w", encoding="utf-8") as f:
            f.write(rsp.text)   #write response to a file

        rsp_json = rsp.json()
        [cont, statuses, length, folderid] = get_objs(rsp_json)
        #print(cont) # No. of jobs in wait state
        if cont == 0:
           print("No jobs are in wait state.")
        else:
            print(f"Number of jobs in wait state are: {length}")
            body = ""
            for folderID in folderid:   #Iterate through each folder ID
                #print(folderID)
                body1 = ""
                job_count = 0
                foldername = get_obj_folderName(statuses, folderID)
                print(f"\n########Folder Name is {foldername}########")
                jobid = [job.get("jobId") for job in statuses if job.get("type") in ["Job", "Command"] and job.get("folderId") == folderID]
                cyclic_folder = next((job.get("cyclic") for job in statuses if job.get("jobId") == folderID), None)

                for jobID in jobid: #Iterate thorugh each jon in the Folder
                    #print(jobID)
                    [jobname, crnttime] = get_obj_jobname(statuses, jobID)
                    print(f'\nJob name is "{jobname}" & jobID is {jobID}')
#                   crnttime = list(crnttime)
                    curnt_start_time = crnttime[0]
                    #print("Current start time is:", curnt_start_time)
                    if not os.path.exists(ref_file_path):
                        print(f"Error: Exported viewpoint file at '{ref_file_path}' does not exist.")
                        sys.exit(1)
                    sch_rsp = get_statuses_from_file(ref_file_path)
                    sch_statuses = sch_rsp.get("statuses", [])
                    [jobname1, scheduled_start_time] = get_obj_jobname(sch_statuses, jobID)
                    #print("Scheduled Start time is:", scheduled_start_time)
                    sched_time_size = len(scheduled_start_time or [])
                    #print("Scheduled Time size is:", sched_time_size)
                    if sched_time_size == 1:
                        scheduled_start_time = scheduled_start_time[0]
                        #print("Scheduled Start time is:", scheduled_start_time)


                    # On demand job handelling
                    if sched_time_size == 0:
                        odjob = get_onDemandJob(statuses, jobID, bkpcont, appl, rundate, base_path)
                        sch_rsp = get_statuses_from_file(ref_file_path) #get statuses after adding ODjob to file
                        sch_statuses = sch_rsp.get("statuses", [])
                        [jobname1, scheduled_start_time] = get_obj_jobname(sch_statuses, jobID)
                        #print("Scheduled Start time of a OD job is:", scheduled_start_time)
                        sched_time_size = len(scheduled_start_time)
                        bkpcont += 1
                    # On demand job handelling

                    if sched_time_size > 1: #If the job is cyclic, get the nearest start time to current time from the list of scheduled start times
                        scheduled_start_time = get_nearest_timestamp(scheduled_start_time)
                    scheduled_start_timein_sec = get_date_insec(scheduled_start_time)
                    curnt_start_timein_sec = get_date_insec(curnt_start_time)
                    curnt_timein_sec = int(time.time())
                    curnt_timein_sec_plus = curnt_timein_sec + 3600
                    scheduled_start_time = get_date_pretty(scheduled_start_time)
                    curnt_start_time = get_date_pretty(curnt_start_time)
                    curnt_time = get_date_pretty(datetime.now().strftime("%Y%m%d%H%M%S"))
                    #print("current time in sec is:", curnt_timein_sec_plus, "scdStartTIme in Sec is:", scheduled_start_timein_sec, "curnt start time in Sec is:", curnt_timein_sec)
                    print(f"Scheduled Start Time is: {scheduled_start_time}\nEstimated start time is: {curnt_start_time}\n Current time in sec is: {curnt_time}")

                    if scheduled_start_timein_sec <= curnt_timein_sec_plus:  #alert 1Hr before the Scheduled start time
                        if curnt_start_timein_sec != scheduled_start_timein_sec:
                            diff_sec = abs(curnt_start_timein_sec - scheduled_start_timein_sec)
                            diff_min = diff_sec // 60
                            days = diff_sec // 86400
                            hours = (diff_sec % 86400) // 3600
                            minutes = (diff_sec % 3600) // 60
                            cyclic = next((job.get("cyclic") for job in statuses if job.get("jobId") == jobID), None)
                            if not cyclic and not cyclic_folder: #Alert only if job & Folder are non-cyclic
                                if diff_min > threshold:
                                    #pdb.set_trace()    #set a break point by inserting pdb.set_trace() to pause execution at this point & start debugging for troubleshoot
                                    job_count += 1
                                    print(f"{Fore.RED}Non-cyclic Job is delayed above the {threshold}min threshold. Delayed by {days}Day/s {hours}Hour/s {minutes}Min")
                                    body1 += f"\nJob Name: {jobname}, Job ID: {jobID}\nScheduled start time: {scheduled_start_time}\n Estimated start time: {curnt_start_time}\nDelayed by {days}Day/s {hours}Hour/s {minutes}Min/s\n"
                                    job_status = next((job.get("status") for job in statuses if job.get("jobId") == jobID and job.get("type") in ["Job", "Command"]), None)
                                    if not job_status:
                                        print(f"  Warning: No wait status found for the job")
                                        body1 += f"\n   Warning: No wait status found for job"
                                    elif job_status.startswith("Wait"):
                                        wait_details = get_set_with_jobid(jobID, env, 'waitingInfo')
                                        print(f"  Job is in wait state due to: {job_status}")
                                        body1 += f"  Job is in wait state due to: {job_status}\n"
                                        #print(wait_details.text)
                                        #pool_name = get_pool_name(wait_details.text)
                                        pool_name = extract_text(wait_details.text, 'The Job is waiting for resource ', ', Quantity')


                                        if pool_name: 
                                            job = None                                           
                                            for poolname in pool_name:
                                                params = {
                                                "resourcePool" : poolname
                                                }
                                                poolstat, sts_code = get_ctm_response(params, env, 'run')
                                                #pooljson = poolstat.json()
                                                #rsp_pool = poolstat.get("statuses", [])
                                                #rsp_pool = poolstat.text
                                                rsp_pool_json = json.loads(poolstat.text)
                                                rsp_pool = json.loads(poolstat.text).get("statuses", [])
                                                #rsp_pool = rsp_data.get("statuses", [])
                                                pool_job = next((job.get("name") for job in rsp_pool if job.get("status") == "Executing" and job.get("type") != "Folder"), None)
                                                pool_folder = next((job.get("name") for job in rsp_pool if job.get("type") == "Folder"), None)
                                                pool_jobid = next((job.get("jobId") for job in rsp_pool if job.get("status") == "Executing" and job.get("type") != "Folder"), None)
                                                '''strt_time = next((job.get("startTime") for job in rsp_pool if job.get("status") == "Executing" and job.get("type") != "Folder"), None)
                                                pool_strt_time = datetime.strptime(strt_time, "%Y%m%d%H%M%S")
                                                now_time = datetime.now()
                                                elapsed_time = str(now_time - pool_strt_time).split('.')[0]
                                                stat = get_set_with_jobid(pool_jobid, env, 'statistics') # get statistics of the job with jobID
                                                stat_json = json.loads(stat.text)'''
                                                [start_time, elapsed_time, stat_time] = get_statistics(rsp_pool_json, pool_jobid, job)

                                                print(
                                                    f"   Resource {poolname} is being used by the job: '{pool_job} ({pool_jobid})', from the folder '{pool_folder}'\n"
                                                    f"       This job '{pool_job}' is started at '{start_time}' and is still executing since {elapsed_time} Min\n"
                                                    f"       This job usually completes it's execution in '{stat_time}' as per the statistics\n"
                                                )
                                                body1 += (
                                                            f"   Resource '{poolname}' is being used by the job: '{pool_job}' ({pool_jobid}) from the folder '{pool_folder}'.\n"
                                                            f"       This job was started at '{start_time}' and is still executing since {elapsed_time} Min.\n"
                                                            f"       This job usually completes its execution in '{stat_time}' as per the statistics.\n"
                                                        )

                                        wait_event = extract_text(wait_details.text, 'The Job is dependant on condition ', '_OK|$')
                                        #wait_event = get_wait_events(wait_details.text)
                                        if wait_event:
                                            for waitevent in wait_event:
                                                print(f"  Waiting on Event: {waitevent}")
                                                body1 += f"  Waiting on Event: {waitevent}\n"
                                                if "-TO-" in waitevent:
                                                        job1, job = waitevent.split("-TO-", 1)
                                                        folder = foldername
                                                        job = job1
                                                elif "." in waitevent:
                                                        folder, job = waitevent.split(".", 1)
                                                else:
                                                    folder = waitevent
                                                    job = None
                                                # is folder in current Viewpoint
                                                j, f = False, False
                                                if job:
                                                    params = {
                                                        "application": appl,
                                                        #"folder": folder,
                                                        "jobname": job,
                                                        "orderDateFrom": rundate
                                                    }
                                                    rsp, sts_code = get_ctm_response(params, env, 'run')   # get response
                                                    rsp_json = json.loads(rsp.text)
                                                    if rsp_json.get("returned") != 0:
                                                        job_status = next((job.get("status") for job in rsp_json.get("statuses", []) if job.get("type") != "Folder"), None)
                                                        job_id_event = next((job.get("jobId") for job in rsp_json.get("statuses", []) if job.get("type") != "Folder"), None)
                                                        print(f"     Job '{job} ({job_id_event})' is in current Viewpoint & is in wait status due to:'{job_status}'")
                                                        body1 += f"     Job '{job} ({job_id_event})' is in current Viewpoint & is in wait status due to: '{job_status}'\n"
                                                        if job_status == "Executing":
                                                            [start_time, elapsed_time, stat_time] = get_statistics(rsp_json, job_id_event, job)
                                                            print(
                                                                f"        This Job '{job} ({job_id_event})' is started at '{start_time}' and is still executing since {elapsed_time} Min\n"
                                                                f"        This Job usually completes it's execution in '{stat_time}' as per the statistics\n"
                                                            )
                                                            body1 += (
                                                                f"        This Job '{job} ({job_id_event})' was started at '{start_time}' and is still executing since {elapsed_time} Min.\n"
                                                                f"        This Job usually completes its execution in '{stat_time}' as per the statistics.\n"
                                                            )
                                                    else:
                                                        print(f"     Event job '{waitevent}' is not in current Viewpoint")
                                                        body1 += f"     Event job '{waitevent}' is not in current Viewpoint\n"
                                                        j = True
                                                else:
                                                    params = {
                                                    "application": appl,
                                                    "folder": folder,
                                                    "orderDateFrom": rundate
                                                    }
                                                    rsp, sts_code = get_ctm_response(params, env, 'run')   # get response
                                                    rsp_json = json.loads(rsp.text)
                                                    if rsp_json.get("returned") != 0:
                                                        job_status = next((job.get("status") for job in rsp_json.get("statuses", []) if job.get("type") == "Folder"), None)
                                                        folder_id_event = next((job.get("jobId") for job in rsp_json.get("statuses", []) if job.get("type") == "Folder"), None)
                                                        print(f"     Folder '{folder} ({folder_id_event})' is in current Viewpoint & is in wait status due to: '{job_status}'")
                                                        body1 += f"     Folder '{folder}' is in current Viewpoint & is in wait status due to: '{job_status}'\n"
                                                        if job_status == "Executing":
                                                            [start_time, elapsed_time, stat_time] = get_statistics(rsp_json, folder_id_event, job)
                                                            print(
                                                                f"        This folder '{folder} ({folder_id_event})' is started at '{start_time}' and is still executing since {elapsed_time} Min\n"
                                                                f"        This folder usually completes it's execution in '{stat_time}' as per the statistics.\n"
                                                            )
                                                            body1 += (
                                                                f"        This folder '{folder} ({folder_id_event})' was started at '{start_time}' and is still executing since {elapsed_time} Min.\n"
                                                                f"        This folder usually completes its execution in '{stat_time}' as per the statistics.\n"
                                                            )
                                                    else:
                                                        print(f"  Event folder '{waitevent} ({folder_id_event})' is not in current Viewpoint\n")                                                
                                                        body1 += f"  Event folder '{waitevent} ({folder_id_event})' is not in current Viewpoint\n"
                                                        f = True
                                                # is folder in current Viewpoint
                                                #get Waiting event details from Control-M planing
                                                if j or f:
                                                    params = {
                                                        "server": "IN01",
                                                        "folder": folder,                                            
                                                        "useArrayFormat": "false"
                                                    }
                                                    rsp_pln, sts_code = get_ctm_response(params, env, 'deploy')
                                                    if sts_code == 200:
                                                        rsp_pln_json = json.loads(rsp_pln.text)
                                                        details = get_details_frm_planning_fldr(rsp_pln_json)
                                                        print(
                                                            f"    The folder '{details['folder_name']}' is using the calendar: '{details['f_included_calendars']}'\n"
                                                            f"        Scheduled run time: '{details['f_fromtime']}' to '{details['f_totime']}'\n"
                                                            f"        Scheduled weekdays: '{details['f_weekdays']}', month days: '{details['f_monthdays']}', months: '{details['f_months']}'\n"
                                                            f"        Waiting on events: '{details['f_events_to_wait']}'\n"
                                                        )
                                                        body1 += (
                                                            f"    The folder '{details['folder_name']}' is using the calendar: '{details['f_included_calendars']}'\n"
                                                            f"        Scheduled run time is between: '{details['f_fromtime']}' and '{details['f_totime']}'\n"
                                                            f"        Scheduled Week days: '{details['f_weekdays']}', Month days: '{details['f_months']}', Months: '{details['f_monthdays']}'\n"
                                                            f"        Waiting on events: '{details['f_events_to_wait']}'\n"
                                                        )
                                                    else:
                                                        print(f"  Warning: Could not retrieve planning details for folder '{folder}'. Error: {rsp_pln}")
                                                        body1 += f"  Warning: Could not retrieve planning details for folder '{folder}'. Error: {rsp_pln}\n"
                                                    if job:
                                                        params["job"] = job
                                                        rsp_pln, sts_code = get_ctm_response(params, env, 'deploy')
                                                        if sts_code == 200:
                                                            rsp_pln_json = json.loads(rsp_pln.text)
                                                            details = get_details_frm_planning_job(rsp_pln_json)
                                                            print(
                                                                f"    The job '{details['job_name']}' is using the calendar: '{details['j_included_calendars']}'\n"
                                                                f"        Scheduled run time: '{details['j_fromtime']}' to '{details['j_totime']}'\n"
                                                                f"        Scheduled weekdays: '{details['j_weekdays']}', month days: '{details['j_monthdays']}', months: '{details['j_months']}'\n"
                                                                f"        Waiting on events: '{details['j_events_to_wait']}'\n"
                                                            )

                                                            body1 += (
                                                                f"    The job '{details['job_name']}' is using the calendar: '{details['j_included_calendars']}'\n"
                                                                f"        Scheduled run time: '{details['j_fromtime']}' to '{details['j_totime']}'\n"
                                                                f"        Scheduled weekdays: '{details['j_weekdays']}', month days: '{details['j_monthdays']}', months: '{details['j_months']}'\n"
                                                                f"        Waiting on events: '{details['j_events_to_wait']}'\n"
                                                            )
                                                        else:
                                                            print(f"  Warning: Could not retrieve planning details for job '{job}' in folder '{folder}'. Error: {rsp_pln}")
                                                            body1 += f"  Warning: Could not retrieve planning details for job '{job}' in folder '{folder}'. Error: {rsp_pln}\n"

                                                #get Waiting event details from Control-M planing
                                                
                                    else:
                                        print(f"Job is in {job_status}")
                                        body1 += f"Job is in {job_status}"
                                else:
                                    print(f"Non-cyclic Job delayed by {diff_min} Min, which is below than the {threshold}min threshold, jobID is {jobID}")
                            else:
                                print(f"Delayed cyclic jobID is {jobID} & Job delayed by {days}Day/s {hours}Hour/s {minutes}Min")
                        else:
                            curnt_timein_sec = int(time.time())
                            curnt_time = get_date_pretty(datetime.now().strftime("%Y%m%d%H%M%S"))
                            if curnt_start_timein_sec < curnt_timein_sec:    #Job start time is < current time but not started
                                diff_min = (abs(curnt_timein_sec - curnt_start_timein_sec)) / 60
                                if diff_min > threshold: #if diff_min is greater than 30min
                                    job_count += 1
                                    print(f'{Fore.RED}Job start time is same as scheduled, but delayed WRT current time {curnt_time} by {diff_min} Sec')
                                    body1 += f'Job Name: {jobname}, Job ID: {jobID}\nScheduled start time: {scheduled_start_time}\n Estimated start time: {curnt_start_time}\nJob start time is same as scheduled, but delayed by {diff_min} Sec WRT current time {curnt_time}\n'
                            else:
                                 print(f"On time job {jobID}")
                    else:
                        print(f'Job\'s scheduled start time is far away from the current time "{curnt_time}".')                
                if job_count != 0:
                    #pdb.set_trace()
                    body += f"\nBelow jobs from the folder {foldername} are being delayed:{body1 or ''}\n"
                    body1 = ""
            if body:
                body = f'This mail is to alert about the jobs delayed more than {threshold}min from their scheduled start time.\nFor the application "{appl}" with run date "{rundate}"\n\n' + body
                subject = f"{appl} delayed job alert"
                send_mail(body, "example@company.com", subject)
                body = ""
            else:
                print(f"\n{Fore.RED}No non-cyclic jobs are being delayed. No mail alert triggered")



if __name__ == "__main__":
    main()