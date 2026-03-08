import os
import requests
from dotenv import load_dotenv
from simple_salesforce import Salesforce

load_dotenv()


def get_token_url(domain=None):
    """Build the correct Salesforce OAuth token URL from domain"""
    sf_domain = domain or os.getenv("SF_DOMAIN", "login")
    if "salesforce.com" in sf_domain:
        return f"https://{sf_domain}/services/oauth2/token"
    return f"https://{sf_domain}.salesforce.com/services/oauth2/token"


def connect_with_oauth(client_id=None, client_secret=None, domain=None):
    """
    PRIMARY connection method.
    Uses OAuth 2.0 Client Credentials — no username/password needed.
    This is the most reliable method for Developer Edition orgs.
    """
    try:
        sf_client_id     = client_id     or os.getenv("SF_CLIENT_ID", "")
        sf_client_secret = client_secret or os.getenv("SF_CLIENT_SECRET", "")
        token_url        = get_token_url(domain)

        response = requests.post(token_url, data={
            "grant_type":    "client_credentials",
            "client_id":     sf_client_id,
            "client_secret": sf_client_secret
        })
        data = response.json()

        if "access_token" not in data:
            return None, f"OAuth Failed: {data.get('error_description', data)}"

        sf = Salesforce(
            instance_url=data["instance_url"],
            session_id=data["access_token"]
        )
        return sf, None

    except Exception as e:
        return None, f"OAuth Error: {str(e)}"


def connect_with_credentials(username=None, password=None,
                              security_token=None,
                              client_id=None, client_secret=None,
                              domain=None):
    """
    FALLBACK connection method.
    Tries Username-Password OAuth flow first.
    If that fails, automatically falls back to Client Credentials.
    """
    try:
        sf_client_id     = client_id      or os.getenv("SF_CLIENT_ID", "")
        sf_client_secret = client_secret  or os.getenv("SF_CLIENT_SECRET", "")
        sf_username      = username       or os.getenv("SF_USERNAME", "")
        sf_password      = password       or os.getenv("SF_PASSWORD", "")
        sf_token         = security_token or os.getenv("SF_SECURITY_TOKEN", "")
        token_url        = get_token_url(domain)

        # Try username-password flow first
        response = requests.post(token_url, data={
            "grant_type":    "password",
            "client_id":     sf_client_id,
            "client_secret": sf_client_secret,
            "username":      sf_username,
            "password":      sf_password + sf_token
        })
        data = response.json()

        if "access_token" in data:
            sf = Salesforce(
                instance_url=data["instance_url"],
                session_id=data["access_token"]
            )
            return sf, None

        # Auto-fallback to Client Credentials
        print("Username-password flow failed, trying Client Credentials...")
        return connect_with_oauth(sf_client_id, sf_client_secret, domain)

    except Exception as e:
        return None, f"Connection Error: {str(e)}"


def get_org_info(sf):
    """Get basic info about the connected Salesforce org"""
    try:
        result = sf.query(
            "SELECT Id, Name, OrganizationType FROM Organization LIMIT 1"
        )
        org = result["records"][0]
        return {
            "org_id":       org.get("Id"),
            "org_name":     org.get("Name"),
            "org_type":     org.get("OrganizationType", "Unknown"),
            "instance_url": sf.base_url
        }
    except Exception as e:
        return {"error": str(e)}


def run_soql_query(sf, query):
    """Run any SOQL query and return clean results"""
    try:
        result  = sf.query_all(query)
        records = []
        for record in result.get("records", []):
            clean = {k: v for k, v in record.items() if k != "attributes"}
            records.append(clean)
        return records, None
    except Exception as e:
        return [], f"SOQL Error: {str(e)}"


def call_salesforce_api(sf, endpoint, method="GET", payload=None):
    """Call any Salesforce REST API endpoint"""
    try:
        headers = {
            "Authorization": f"Bearer {sf.session_id}",
            "Content-Type":  "application/json"
        }
        url = f"{sf.sf_instance}{endpoint}"

        if   method == "GET":    resp = requests.get(url,    headers=headers)
        elif method == "POST":   resp = requests.post(url,   headers=headers, json=payload)
        elif method == "PATCH":  resp = requests.patch(url,  headers=headers, json=payload)
        elif method == "DELETE": resp = requests.delete(url, headers=headers)
        else:
            return None, f"Unsupported method: {method}"

        return {
            "status_code": resp.status_code,
            "response":    resp.json() if resp.content else {},
            "success":     resp.status_code in [200, 201, 204]
        }, None

    except Exception as e:
        return None, f"API Error: {str(e)}"


def create_record(sf, object_name, data):
    try:
        return getattr(sf, object_name).create(data), None
    except Exception as e:
        return None, f"Create Error: {str(e)}"


def get_record(sf, object_name, record_id):
    try:
        result = getattr(sf, object_name).get(record_id)
        return {k: v for k, v in result.items() if k != "attributes"}, None
    except Exception as e:
        return None, f"Get Error: {str(e)}"


def update_record(sf, object_name, record_id, data):
    try:
        getattr(sf, object_name).update(record_id, data)
        return {"updated": True, "id": record_id}, None
    except Exception as e:
        return None, f"Update Error: {str(e)}"


def delete_record(sf, object_name, record_id):
    try:
        getattr(sf, object_name).delete(record_id)
        return {"deleted": True, "id": record_id}, None
    except Exception as e:
        return None, f"Delete Error: {str(e)}"


# ── Quick test ───────────────────────────────────────────────
if __name__ == "__main__":
    print("Testing Salesforce Connection (Client Credentials)...")
    sf, error = connect_with_oauth()

    if sf:
        info = get_org_info(sf)
        print(f"✅ Connected to: {info.get('org_name')} ({info.get('org_type')})")
        print(f"   Instance URL: {info.get('instance_url')}")

        accounts, err = run_soql_query(sf, "SELECT Id, Name FROM Account LIMIT 3")
        if accounts:
            print(f"\n📋 Sample Accounts ({len(accounts)} found):")
            for acc in accounts:
                print(f"   - {acc['Name']}")
        else:
            print("\n📋 No accounts yet (normal for a brand new org)")
    else:
        print(f"❌ Failed: {error}")