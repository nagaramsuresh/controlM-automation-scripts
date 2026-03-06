'''
This script is used to export theapplication specific Viewpoint when executed.
This is usually ran the time when new schedule is loaded.
So that we have the reference file for the application with all the job details which can be used for future reference and analysis.
This file is used with delayedJobAlert.py to analyse the delay in jobs execution and trigger alert

Usage: python exportViewpoint.py <application_name>
Example: python exportViewpoint.py IMF
This script requires atleast one application name as input argument
'''
import sys
from utils.ctm_submodules import get_ctm_response, get_rundate, get_application

def main():

    args = sys.argv[1:]
    arg_cnt = len(args)
    env = 'PROD' # Define environment as PROD, you can change it to DEV or any other environment as per your requirement. Make sure to have the necessary access and permissions to retrieve job details from the specified environment.
    base_path = r'C:/Users/sureshkumar.nagaram/Downloads/ctm' #Define base path to store the reference files exported from viewpoint. Make sure this path has necessary read/write permissions and enough storage space for the files. You can change this path as per your requirement.
    if arg_cnt == 0:
        print("Error: Please provide at least one application name as an argument.")
        sys.exit(1)
    for argmnt in args:
        appl = get_application(argmnt)
        tday = get_rundate(appl)
        params = {
            "application": appl,
            "orderDateTo": tday
        }

        rsp, sts_code = get_ctm_response(params, env, 'run')
        with open(rf"{base_path}\{appl}jobs{tday}.json", "w", encoding="utf-8") as f:   # Write the response to a file in the specified base path with the application name and run date in the file name for easy identification and reference. The file will be saved in JSON format with UTF-8 encoding to preserve any special characters in the job details.

            f.write(rsp.text)

if __name__ == "__main__":
    main()