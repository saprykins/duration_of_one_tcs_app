import logging
import azure.functions as func
import pandas as pd
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    if name:
        ORGANIZATION_NAME = "g*"
        PROJECT_NAME = "A*"

        # ADO
        pat = "r*"
        
        # blob
        connect_str = "D*"

        file_name = 'tcs_duration.csv'
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
        df_duration = pd.DataFrame([], columns = cols_duration)
        df_duration.to_csv(file_name, index=False)

        # Send the CSV file to Azure Blob Storage
        
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_name = "strcontainertcsduration"
        container_client = blob_service_client.get_container_client(container_name)
        blob_name = file_name

        with open(file_name, "rb") as data:
            container_client.upload_blob(name=blob_name, data=data)

        container_client.close()
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )
