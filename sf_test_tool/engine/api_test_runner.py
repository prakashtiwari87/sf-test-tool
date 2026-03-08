import json
from connectors.salesforce_connector import (
    call_salesforce_api, create_record, get_record, update_record, delete_record
)

def run_api_test(sf, test_case, input_data):
    """
    Execute a Salesforce API test case.
    Supports GET, POST, PATCH, DELETE on any Salesforce REST endpoint.
    Also supports CRUD operations on standard and custom objects.
    """
    action = test_case.get("action", "GET").upper()
    sf_object = test_case.get("sf_object", "")
    
    # If endpoint is directly specified in input_data as a path
    if isinstance(input_data, str) and input_data.startswith("/services"):
        result, error = call_salesforce_api(sf, input_data, method=action)
        if error:
            return None, error
        return json.dumps(result, indent=2), None

    # CRUD operations on Salesforce objects
    if action == "GET" and isinstance(input_data, str) and len(input_data) == 18:
        # Looks like a Salesforce Record ID
        result, error = get_record(sf, sf_object, input_data)
        if error:
            return None, error
        return json.dumps(result, indent=2), None

    elif action in ["POST", "CREATE"]:
        data = input_data if isinstance(input_data, dict) else {}
        result, error = create_record(sf, sf_object, data)
        if error:
            return None, error
        return f"Record created successfully. ID: {result.get('id', 'Unknown')}", None

    elif action in ["PATCH", "UPDATE"]:
        data = input_data if isinstance(input_data, dict) else {}
        record_id = data.pop("Id", None) or data.pop("id", None)
        if not record_id:
            return None, "UPDATE action requires 'Id' field in Input_Data"
        result, error = update_record(sf, sf_object, record_id, data)
        if error:
            return None, error
        return f"Record {record_id} updated successfully", None

    elif action == "DELETE":
        record_id = input_data if isinstance(input_data, str) else input_data.get("Id")
        if not record_id:
            return None, "DELETE action requires a record ID"
        result, error = delete_record(sf, sf_object, record_id)
        if error:
            return None, error
        return f"Record {record_id} deleted successfully", None

    # Generic REST API call
    endpoint = f"/services/data/v59.0/sobjects/{sf_object}/"
    result, error = call_salesforce_api(sf, endpoint, method=action, payload=input_data)
    if error:
        return None, error
    return json.dumps(result, indent=2), None