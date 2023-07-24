import logging
import azure.functions as func

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Azure DevOps webhook received.')

    try:
        # Get the payload from the request body
        payload = req.get_json()

        # Extract the "Custom.app_id" field value as a float
        app_id_float = payload['resource']['fields']['Custom.app_id']

        # Convert the float value to an integer
        app_id_integer = int(app_id_float)

        # Process the app_id_integer as needed
        # ...

        return func.HttpResponse(f"Custom.app_id: {app_id_integer}", status_code=200)

    except Exception as e:
        return func.HttpResponse(f"Error processing the webhook payload: {str(e)}", status_code=500)
