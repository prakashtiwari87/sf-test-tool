"""
prompt_parser.py
Parses natural language test prompts into structured instructions.
Extracts: object, operation, record count, included fields,
          excluded fields, field values, and constraints.
No hallucinations — only acts on what the user explicitly says.
"""

import json
from connectors.llm_connector import get_llm_response


# ─────────────────────────────────────────────────────────────
# FIELD GROUP MAPPINGS
# ─────────────────────────────────────────────────────────────

FIELD_GROUPS = {
    "phone fields": [
        "Phone", "MobilePhone", "HomePhone",
        "OtherPhone", "AssistantPhone", "Fax"
    ],
    "phone": [
        "Phone", "MobilePhone", "HomePhone",
        "OtherPhone", "AssistantPhone", "Fax"
    ],
    "address fields": [
        "MailingStreet", "MailingCity", "MailingState",
        "MailingStateCode", "MailingPostalCode", "MailingCountry",
        "MailingCountryCode", "MailingLatitude", "MailingLongitude",
        "OtherStreet", "OtherCity", "OtherState",
        "OtherStateCode", "OtherPostalCode", "OtherCountry",
        "OtherCountryCode", "OtherLatitude", "OtherLongitude",
        "BillingStreet", "BillingCity", "BillingState",
        "BillingStateCode", "BillingPostalCode", "BillingCountry",
        "BillingCountryCode", "BillingLatitude", "BillingLongitude",
        "ShippingStreet", "ShippingCity", "ShippingState",
        "ShippingStateCode", "ShippingPostalCode", "ShippingCountry",
        "ShippingCountryCode", "ShippingLatitude", "ShippingLongitude",
        "Street", "City", "State", "StateCode",
        "PostalCode", "Country", "CountryCode",
        "Latitude", "Longitude", "GeocodeAccuracy"
    ],
    "mailing address": [
        "MailingStreet", "MailingCity", "MailingState",
        "MailingStateCode", "MailingPostalCode", "MailingCountry",
        "MailingCountryCode", "MailingLatitude", "MailingLongitude"
    ],
    "other address": [
        "OtherStreet", "OtherCity", "OtherState",
        "OtherStateCode", "OtherPostalCode", "OtherCountry",
        "OtherCountryCode"
    ],
    "billing address": [
        "BillingStreet", "BillingCity", "BillingState",
        "BillingStateCode", "BillingPostalCode", "BillingCountry",
        "BillingCountryCode"
    ],
    "shipping address": [
        "ShippingStreet", "ShippingCity", "ShippingState",
        "ShippingStateCode", "ShippingPostalCode", "ShippingCountry",
        "ShippingCountryCode"
    ],
    "name fields": [
        "FirstName", "LastName", "Salutation", "Suffix"
    ],
    "social fields": [
        "Twitter__c", "LinkedIn__c", "Facebook__c",
        "TwitterHandle", "LinkedInUrl"
    ],
    "description fields": [
        "Description", "Bio__c", "Notes__c"
    ],
}


def _expand_field_groups(field_mentions: list) -> list:
    """Expand group names like 'phone fields' into actual field names."""
    expanded = []
    for mention in field_mentions:
        mention_lower = mention.lower().strip()
        matched = False
        for group_key, group_fields in FIELD_GROUPS.items():
            if group_key in mention_lower or mention_lower in group_key:
                expanded.extend(group_fields)
                matched = True
                break
        if not matched:
            expanded.append(mention)
    return list(set(expanded))


def parse_test_prompt(prompt: str,
                      llm_model: str = "groq/llama-3.3-70b-versatile"
                      ) -> dict:
    """
    Parse a natural language test prompt into structured instructions.

    Returns a dict with:
    - operation:             create / query / update / delete
    - object_name:           Salesforce object API name
    - record_count:          how many records to create
    - include_fields:        explicit list of fields to include
    - exclude_fields:        explicit list of fields to NEVER populate
    - exclude_field_groups:  group names to exclude
    - field_values:          specific values mentioned
    - constraints:           any other rules
    - raw_prompt:            original prompt
    """
    # Build the prompt using string concatenation to avoid
    # f-string conflicts with JSON curly braces
    parse_prompt_text = (
        'Analyze this Salesforce test instruction carefully '
        'and extract structured information.\n\n'
        'Instruction: "' + prompt + '"\n\n'
        'Return ONLY a valid JSON object with these exact fields:\n\n'
        '{\n'
        '  "operation": "create",\n'
        '  "object_name": "Contact",\n'
        '  "record_count": 1,\n'
        '  "include_fields": ["FirstName", "LastName", "Email"],\n'
        '  "exclude_fields": ["MailingStreet", "MailingCity"],\n'
        '  "exclude_field_groups": ["address fields"],\n'
        '  "field_values": {"AccountId": "use_existing"},\n'
        '  "constraints": ["return RecordIDs"]\n'
        '}\n\n'
        'Rules for parsing:\n'
        '- operation: create/query/update/delete\n'
        '- object_name: exact Salesforce API object name\n'
        '  (Contact, Account, Lead, Opportunity, Case, Task, Event)\n'
        '- record_count: number of records, default 1\n'
        '- include_fields: ONLY fields the user explicitly mentioned.\n'
        '  Map common names to API names:\n'
        '  "First Name" -> "FirstName"\n'
        '  "Last Name" -> "LastName"\n'
        '  "Account Name" -> "AccountId"\n'
        '  "Email" -> "Email"\n'
        '  "Title" -> "Title"\n'
        '  "Department" -> "Department"\n'
        '  "Phone" -> "Phone"\n'
        '  If user says "all phone fields" put "phone fields" as-is.\n'
        '- exclude_fields: fields the user said NOT to fill.\n'
        '  If user says "do not fill address fields" expand to:\n'
        '  MailingStreet, MailingCity, MailingState, MailingStateCode,\n'
        '  MailingPostalCode, MailingCountry, MailingCountryCode,\n'
        '  OtherStreet, OtherCity, OtherState, OtherPostalCode,\n'
        '  OtherCountry, OtherCountryCode\n'
        '- exclude_field_groups: group names e.g. ["address fields"]\n'
        '- field_values: If user says "select any existing Account"\n'
        '  set AccountId to "use_existing"\n'
        '- constraints: special instructions like "return RecordIDs"\n\n'
        'Be very precise. Only include what the user explicitly said.\n'
        'Return ONLY the JSON object. No explanation. No markdown.'
    )

    resp, err = get_llm_response(
        parse_prompt_text, model=llm_model, max_tokens=600
    )
    if err or not resp:
        return _default_parse_result(prompt)

    try:
        clean = (
            resp.strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )
        parsed = json.loads(clean)

        # Expand field group names in include list to real field names
        if parsed.get("include_fields"):
            parsed["include_fields"] = _expand_field_groups(
                parsed["include_fields"]
            )

        # Expand exclude groups into actual field names
        excluded = set(parsed.get("exclude_fields", []))
        for group in parsed.get("exclude_field_groups", []):
            group_lower = group.lower()
            if group_lower in FIELD_GROUPS:
                excluded.update(FIELD_GROUPS[group_lower])
            for group_key, group_vals in FIELD_GROUPS.items():
                if group_lower in group_key or group_key in group_lower:
                    excluded.update(group_vals)

        parsed["exclude_fields"] = list(excluded)
        parsed["raw_prompt"]     = prompt

        try:
            parsed["record_count"] = int(parsed.get("record_count", 1))
        except (TypeError, ValueError):
            parsed["record_count"] = 1

        return parsed

    except Exception:
        return _default_parse_result(prompt)


def _default_parse_result(prompt: str) -> dict:
    """Fallback parse result when LLM parsing fails"""
    return {
        "operation":            "create",
        "object_name":          "Contact",
        "record_count":         1,
        "include_fields":       [],
        "exclude_fields":       [],
        "exclude_field_groups": [],
        "field_values":         {},
        "constraints":          [],
        "raw_prompt":           prompt
    }


def build_field_list(parsed: dict,
                     createable_fields: list) -> list:
    """
    Build the final list of fields to populate based on:
    1. What the user explicitly included
    2. What the user explicitly excluded
    3. What is actually createable in Salesforce
    Always excludes system fields regardless of user input.
    """
    include = set(parsed.get("include_fields", []))
    exclude = set(parsed.get("exclude_fields", []))

    always_exclude = {
        'Id', 'OwnerId', 'CreatedDate', 'CreatedById',
        'LastModifiedDate', 'LastModifiedById',
        'SystemModstamp', 'IsDeleted', 'LastActivityDate',
        'LastViewedDate', 'LastReferencedDate',
        'MasterRecordId', 'IsEmailBounced',
        'EmailBouncedDate', 'EmailBouncedReason',
        'Jigsaw', 'JigsawContactId', 'IndividualId',
        'CleanStatus', 'ConnectionReceivedId',
        'ConnectionSentId', 'PhotoUrl',
        'HasOptedOutOfEmail', 'HasOptedOutOfFax', 'DoNotCall',
    }
    exclude.update(always_exclude)

    final_fields = []
    for field in createable_fields:
        fname  = field["field_name"]
        flabel = field.get("field_label", "")

        if fname in exclude:
            continue

        if include:
            if fname in include or flabel in include:
                final_fields.append(field)
        else:
            final_fields.append(field)

    return final_fields


def get_field_generation_prompt(parsed: dict,
                                 fields: list,
                                 object_name: str,
                                 record_index: int = 1) -> str:
    """
    Build a strict LLM prompt for generating field data.
    Uses string concatenation — no f-strings with JSON to avoid
    syntax conflicts with curly braces.
    """
    field_context = []
    for f in fields:
        fc = {
            "name":     f["field_name"],
            "type":     f["field_type"],
            "required": bool(f["is_required"])
        }
        if f.get("picklist_values"):
            try:
                vals = json.loads(f["picklist_values"])
                if vals:
                    fc["allowed_values"] = vals[:5]
            except Exception:
                pass
        field_context.append(fc)

    exclude_groups = parsed.get("exclude_field_groups", [])
    exclude_fields = parsed.get("exclude_fields", [])
    field_values   = parsed.get("field_values", {})
    raw_prompt     = parsed.get("raw_prompt", "")

    # Build exclusion section
    sample_excludes = [
        f for f in list(exclude_fields)[:15]
        if f not in {
            'Id', 'OwnerId', 'CreatedDate', 'CreatedById',
            'LastModifiedDate', 'LastModifiedById',
            'SystemModstamp', 'IsDeleted'
        }
    ]

    exclusion_section = ""
    if exclude_groups or sample_excludes:
        exclusion_section = (
            "\nSTRICT EXCLUSIONS — Do NOT include ANY of these fields:\n"
            "Excluded groups : "
            + (", ".join(exclude_groups) if exclude_groups else "none")
            + "\nExcluded fields : "
            + (", ".join(sample_excludes) if sample_excludes else "none")
            + "\n"
        )

    # Build specific values section
    values_section = ""
    if field_values:
        safe_vals = {
            k: v for k, v in field_values.items()
            if str(v).lower() != "use_existing"
        }
        if safe_vals:
            values_section = (
                "\nUse these specific values:\n"
                + json.dumps(safe_vals, indent=2)
                + "\n"
            )

    return (
        "Generate realistic test data for Salesforce "
        + object_name
        + " record #"
        + str(record_index)
        + ".\n\n"
        "AVAILABLE FIELDS — use ONLY these exact field names:\n"
        + json.dumps(field_context, indent=2)
        + "\n"
        + exclusion_section
        + values_section
        + "\nSTRICT RULES:\n"
        "1. Use ONLY field names from AVAILABLE FIELDS above\n"
        "2. Do NOT add any field not in that list\n"
        "3. Do NOT include Id, OwnerId or any system fields\n"
        "4. Required fields (required=true) MUST have a value\n"
        "5. Picklist fields MUST use one of allowed_values exactly\n"
        "6. Emails: @testcompany.com domain only\n"
        "7. Phone: 555-0100 to 555-0199 format only\n"
        "8. Make record #"
        + str(record_index)
        + " clearly different from other records\n"
        "9. Return ONLY a valid JSON object — no markdown\n\n"
        'Original instruction: "' + raw_prompt + '"'
    )