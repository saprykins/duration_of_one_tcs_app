# 0/ access to calls
# in azure - allow calls from externals
# 2/ hide connections
# 3/ where do we specify environment 
# - during project creation
# - in vscode corner
# 4/ tbc W approach: no import 
# 5/ contact smn in D

import logging
import azure.functions as func
import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
import sys
import requests
import json
import base64
from datetime import datetime
import time

ORGANIZATION_NAME = "g*"
PROJECT_NAME = "A*"

# ADO
pat = "r*"

# blob
connect_str = "D*"

container_name = "strcontainertcsduration"

authorization = str(base64.b64encode(bytes(':'+pat, 'ascii')), 'ascii')

cols_duration =  [
    # updates needed
    "App id", 
    "App name", 
    #"Feature id", 
    #"Feature", 
    #"User story id", 
    #"User story", 
    "Task id", 
    "Task",
    "Task description",
    "Start time",
    "End time",
    "Duration (min)"
]







def get_childs_list(app_id):
    #
    # Can be used to get all types of childs (user stories, features ...)
    #

    url = f"https://dev.azure.com/{ORGANIZATION_NAME}/{PROJECT_NAME}/_apis/wit/workitems/{app_id}/?$expand=all"
    # print(url)
    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization,
    }
    response = requests.get(url, headers=headers)
    response_json = json.loads(response.text)

    user_story_work_items = response_json["relations"]

    child_ids = []
    for relation in user_story_work_items:
        if relation["rel"] == "System.LinkTypes.Hierarchy-Forward":
            url = relation["url"]
            parts = url.split('/')
            id = parts[-1]
            child_ids.append(id)
    childs_work_item_ids = child_ids
    return childs_work_item_ids





def get_duration(workitem_id):
    #
    # duration for tasks only
    #

    url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/' + PROJECT_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '/updates?api-version=7.0'

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )
    changes = response.json()["value"]

    for state_change in reversed(changes):
        try:
            title = state_change["fields"]["Custom.PlaybookActivities"]['newValue']
            task_description = state_change["fields"]["Custom.PlaybookSubActivities"]['newValue']
            break
        except:
            title = None
            task_description = None


    app_history = response.json()["value"]

    status_change = None

    for state_change in reversed(app_history):
        try:
            if state_change["fields"]["System.State"]['oldValue'] == "Active" and state_change["fields"]["System.State"]['newValue'] == "Closed":
                status_change = state_change
                break
        except:
            val = 0

    # Calculate the duration of the work item in progress
    if status_change is not None:
        try:
            start_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue']
            end_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue']

            in_progress_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue'], '%Y-%m-%dT%H:%M:%S.%fZ')
            closed_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue'], '%Y-%m-%dT%H:%M:%S.%fZ')

            duration = closed_date - in_progress_date

            duration_sec = duration.seconds
            duration_min = duration_sec/60

        except:
            duration_min = None
            start_time = None
            end_time = None
    else:
        duration_min = None
        start_time = None
        end_time = None

    if duration_min is not None:
        duration_min = round(duration_min)

    #
    # If closed without in progress
    #

    for state_change in reversed(app_history):
        try:
            if state_change["fields"]["System.State"]['oldValue'] == "To Do" and state_change["fields"]["System.State"]['newValue'] == "Closed":
                status_change = state_change
                break
        except:
            val = 0

    # Calculate the duration of the work item in progress
    if status_change is not None:
        try:
            # start_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['oldValue']
            end_time = status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue']
            closed_date = datetime.strptime(status_change["fields"]['Microsoft.VSTS.Common.StateChangeDate']['newValue'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            duration_min = None
            start_time = None
            end_time = None
    # end of closed w/o in progress


    return (duration_min, title, task_description, start_time, end_time)





def get_app_title(workitem_id):
    #
    # 
    #
    url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '?$expand=all'
    # print(url)
    # url = 'https://dev.azure.com/' + ORGANIZATION_NAME + '/' + PROJECT_NAME + '/_apis/wit/workItems/' + str(workitem_id) + '/updates?api-version=7.0'

    headers = {
        'Accept': 'application/json',
        'Authorization': 'Basic '+ authorization
    }
    response = requests.get(
        url = url,
        headers=headers,
    )

    try:
        title = response.json()["fields"]["System.Title"]
    except:
        title = None

    return title



def save_duration_to_df(app_id, df_duration):
    #
    #
    #
    app_title = get_app_title(app_id)

    task_ids = get_childs_list(app_id)

    for task_id in task_ids:
        # duration, task_title, start_time, end_time = get_duration(task_id)
        duration, task_title, task_description, start_time, end_time = get_duration(task_id)
        new_row = [app_id, app_title, task_id, task_title, task_description, start_time, end_time, duration]
        # new_row = [app_id, app_title, feature_id, feature_title, user_story_id, user_story_title, task_id, task_title, start_time, end_time, duration]
        new_df = pd.DataFrame([new_row], columns=cols_duration)
        df_duration = pd.concat([df_duration, new_df], ignore_index = True)

    return df_duration



def update_workitem_description(new_description, workitem_id):
    # 
    # to save to workitem data received after fnc terminated
    # can be link to bucket
    # 
    url = f"https://dev.azure.com/{organization}/{project}/_apis/wit/workitems/{workitem_id}?api-version=7.0"

    headers = {
        "Content-Type": "application/json-patch+json"
    }

    body = [
        {
            "op": "add",
            "path": "/fields/System.Description",
            "value": new_description
        }
    ]

    r = requests.patch(
        url,
        data=json.dumps(body),
        headers=headers,
        auth=("", pat),
    )
    print(r)



def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    # parent_id_int = ''
    try:
        # Get the payload from the request body
        payload = req.get_json()

        # Extract the "Custom.app_id" field value as a float
        parent_id_float = payload['resource']['fields']['Custom.app_id'] # work item id, or where will upload data
        # print(parent_id_float, ' is parent extracted from ADO')
        # Convert the float value to an integer
        
        parent_id_int = int(parent_id_float)
        # print(parent_id_float, ' is parent int extracted from ADO')
        
        parent_id_int = str(parent_id_int)
        # print(parent_id_float, ' is parent str extracted from ADO')
        
        # data = json.loads(json_data)
        #
        #
        #
        wi_id_float = payload['resource']['id']
        wi_id_int = int(wi_id_float)
        #
        #
        #
        # Extract the value "248102" using the "System.Parent" key from the last item in the "value" array
        # parent_id_undefined = data["value"][-1]["fields"]["System.Parent"]["newValue"] # parent id or application
        # parent_id_int = int(parent_id_undefined)
        # parent_id_int = '248102' # template app
        # print(parent_id_int, ' is parent assigned in code')
        

    except Exception as e:
        return func.HttpResponse(f"Error processing the webhook payload: {str(e)}", status_code=500)
    
    if parent_id_int:
        file_name = 'tcs_duration_app_id_' + parent_id_int + '.csv'
        df_duration = pd.DataFrame([], columns = cols_duration)
        # 
        # 
        #
        # parent_id_int = "248102" # OK
        # parent_id_int = 248102 # OK
        #
        #
        #
        df_duration = save_duration_to_df(parent_id_int, df_duration)

        # description_value = df_duration.to_string(index=False)
        # description_value = df_duration.to_json(orient='records')
        # description_value = df_duration.to_dict(orient='records')
        
        df_duration.to_csv(file_name, index=False)

        # Send the CSV file to Azure Blob Storage
        # workitem_id = 291451 # WI to update description to
        # new_description = "This is the updated description for the work item. 2"
        # wi_id_int = '291451' # calculate obj

        

        blob_service_client = BlobServiceClient.from_connection_string(connect_str)

        container_client = blob_service_client.get_container_client(container_name)
        blob_name = file_name

        with open(file_name, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data, overwrite=True)
        
        # URL
        download_url = container_client.url
        
        container_client.close()

        # new_description = df_duration
        new_description = download_url
        # new_description = df_duration.to_string(index=False)
        update_workitem_description(new_description, wi_id_int)
        
        
        return func.HttpResponse(f"Duration for application_id {parent_id_int} was generated successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a 'application id' such as '248102' in the query string or in the request body.",
             status_code=200
        )
