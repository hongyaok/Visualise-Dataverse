"""
Dataverse Web API helper module.

All functions accept instance_url and access_token as parameters —
nothing is hardcoded. Every call is read-only (GET requests only).
"""

import requests
import concurrent.futures


def _headers(access_token: str) -> dict:
    """Standard OData headers for Dataverse Web API calls."""
    return {
        "Authorization": f"Bearer {access_token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
    }


def _ensure_trailing_slash(url: str) -> str:
    """Ensure the instance URL ends with a slash."""
    return url if url.endswith("/") else url + "/"


# ─── Solutions ────────────────────────────────────────────────────────────────


def get_solutions(instance_url: str, access_token: str) -> list[dict]:
    """
    Retrieve all solutions in the environment.

    Returns a list of dicts with keys:
        solutionid, friendlyname, uniquename, version, ismanaged
    """
    base = _ensure_trailing_slash(instance_url)
    url = f"{base}api/data/v9.2/solutions"
    params = {
        "$select": "solutionid,friendlyname,uniquename,version,ismanaged",
        "$filter": "isvisible eq true",
        "$orderby": "friendlyname asc",
    }

    resp = requests.get(url, headers=_headers(access_token), params=params)
    resp.raise_for_status()
    return resp.json().get("value", [])


# ─── Solution Components (Tables) ────────────────────────────────────────────


def get_solution_entity_ids(
    instance_url: str, access_token: str, solution_id: str
) -> list[str]:
    """
    Get all Entity (table) MetadataIds that belong to a solution.

    componenttype 1 = Entity.
    Returns a list of objectid GUIDs.
    """
    base = _ensure_trailing_slash(instance_url)
    url = f"{base}api/data/v9.2/solutioncomponents"
    params = {
        "$filter": (
            f"_solutionid_value eq {solution_id} and componenttype eq 1"
        ),
        "$select": "objectid,componenttype",
    }

    all_ids = []
    while url:
        resp = requests.get(url, headers=_headers(access_token), params=params)
        resp.raise_for_status()
        data = resp.json()
        all_ids.extend(c["objectid"] for c in data.get("value", []))
        # Handle OData pagination
        url = data.get("@odata.nextLink")
        params = None  # nextLink already contains query params

    return all_ids


# ─── Entity Metadata ─────────────────────────────────────────────────────────


def get_table_metadata(
    instance_url: str, access_token: str, entity_metadata_id: str
) -> dict | None:
    """
    Retrieve display name and logical name for a single entity by MetadataId.

    Returns a dict: { MetadataId, LogicalName, DisplayName } or None on error.
    """
    base = _ensure_trailing_slash(instance_url)
    url = (
        f"{base}api/data/v9.2/EntityDefinitions({entity_metadata_id})"
        f"?$select=LogicalName,SchemaName,DisplayName"
    )

    resp = requests.get(url, headers=_headers(access_token))
    if resp.status_code != 200:
        return None

    meta = resp.json()

    # Extract the user-facing display name (fallback to SchemaName)
    display_name = meta.get("SchemaName", meta["LogicalName"])
    try:
        display_name = meta["DisplayName"]["UserLocalizedLabel"]["Label"]
    except (KeyError, TypeError):
        pass

    return {
        "MetadataId": entity_metadata_id,
        "LogicalName": meta["LogicalName"],
        "DisplayName": display_name,
    }


def get_all_tables_in_solution(
    instance_url: str, access_token: str, solution_id: str
) -> list[dict]:
    """
    High-level: get all table metadata for entities in a solution.
    """
    entity_ids = get_solution_entity_ids(instance_url, access_token, solution_id)
    tables = []
    for eid in entity_ids:
        meta = get_table_metadata(instance_url, access_token, eid)
        if meta:
            tables.append(meta)
    return tables


def get_table_details(
    instance_url: str, access_token: str, logical_name: str
) -> dict | None:
    """
    Retrieve all attributes (columns) and metadata for a given table.
    """
    base = _ensure_trailing_slash(instance_url)
    url = (
        f"{base}api/data/v9.2/EntityDefinitions(LogicalName='{logical_name}')"
        f"?$expand=Attributes($select=LogicalName,SchemaName,AttributeType,IsPrimaryId,IsPrimaryName;$filter=IsLogical eq false)"
    )

    resp = requests.get(url, headers=_headers(access_token))
    if resp.status_code != 200:
        return None

    meta = resp.json()
    attributes = []
    for attr in meta.get("Attributes", []):
        attributes.append({
            "logical_name": attr.get("LogicalName"),
            "schema_name": attr.get("SchemaName"),
            "type": attr.get("AttributeType"),
            "is_primary_id": attr.get("IsPrimaryId", False),
            "is_primary_name": attr.get("IsPrimaryName", False),
        })

    # Sort attributes: primary id first, primary name second, then alphabetically
    attributes.sort(key=lambda a: (not a["is_primary_id"], not a["is_primary_name"], a["logical_name"]))

    display_name = meta.get("SchemaName", meta["LogicalName"])
    try:
        display_name = meta["DisplayName"]["UserLocalizedLabel"]["Label"]
    except (KeyError, TypeError):
        pass

    return {
        "LogicalName": meta["LogicalName"],
        "SchemaName": meta.get("SchemaName"),
        "DisplayName": display_name,
        "Attributes": attributes,
    }


def get_all_solution_columns(
    instance_url: str, access_token: str, solution_id: str
) -> dict:
    """
    Fetch all attributes concurrently for every table in the solution.
    Returns a dict mapping LogicalName -> list of Attributes.
    """
    tables = get_all_tables_in_solution(instance_url, access_token, solution_id)
    logical_names = [t["LogicalName"] for t in tables]

    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_name = {
            executor.submit(get_table_details, instance_url, access_token, name): name
            for name in logical_names
        }
        for future in concurrent.futures.as_completed(future_to_name):
            name = future_to_name[future]
            try:
                data = future.result()
                if data:
                    results[name] = data["Attributes"]
            except Exception:
                pass

    return results

# ─── Relationships ────────────────────────────────────────────────────────────


def get_one_to_many_relationships(
    instance_url: str, access_token: str, logical_name: str
) -> list[dict]:
    """
    Get One-to-Many relationships where this table is the *referenced* (one) side.
    """
    base = _ensure_trailing_slash(instance_url)
    url = (
        f"{base}api/data/v9.2/EntityDefinitions(LogicalName='{logical_name}')"
        f"/OneToManyRelationships"
    )
    params = {
        "$select": (
            "SchemaName,ReferencedEntity,ReferencingEntity,"
            "ReferencedAttribute,ReferencingAttribute"
        )
    }

    resp = requests.get(url, headers=_headers(access_token), params=params)
    if resp.status_code != 200:
        return []

    results = []
    for rel in resp.json().get("value", []):
        results.append(
            {
                "type": "1:N",
                "schema_name": rel["SchemaName"],
                "from_table": rel["ReferencedEntity"],
                "to_table": rel["ReferencingEntity"],
                "from_key": rel.get("ReferencedAttribute", ""),
                "via_column": rel.get("ReferencingAttribute", ""),
            }
        )
    return results


def get_many_to_many_relationships(
    instance_url: str, access_token: str, logical_name: str
) -> list[dict]:
    """
    Get Many-to-Many relationships for this table.
    """
    base = _ensure_trailing_slash(instance_url)
    url = (
        f"{base}api/data/v9.2/EntityDefinitions(LogicalName='{logical_name}')"
        f"/ManyToManyRelationships"
    )
    params = {
        "$select": (
            "SchemaName,Entity1LogicalName,Entity2LogicalName,"
            "IntersectEntityName,Entity1IntersectAttribute,Entity2IntersectAttribute"
        )
    }

    resp = requests.get(url, headers=_headers(access_token), params=params)
    if resp.status_code != 200:
        return []

    results = []
    for rel in resp.json().get("value", []):
        results.append(
            {
                "type": "N:N",
                "schema_name": rel["SchemaName"],
                "from_table": rel["Entity1LogicalName"],
                "to_table": rel["Entity2LogicalName"],
                "from_key": rel.get("Entity1IntersectAttribute", ""),
                "to_key": rel.get("Entity2IntersectAttribute", ""),
                "via_table": rel.get("IntersectEntityName", ""),
            }
        )
    return results


# ─── Build Diagram Data ──────────────────────────────────────────────────────


def build_diagram_data(
    instance_url: str, access_token: str, solution_id: str
) -> dict:
    """
    Build the complete diagram payload for the frontend.

    Returns:
        {
            "nodes": [ { "id": "logicalname", "label": "Display Name" }, ... ],
            "edges": [ { "from": "...", "to": "...", "type": "1:N", ... }, ... ],
            "solution_tables": [ "logicalname", ... ]
        }
    """
    # 1. Get all tables in the solution
    tables = get_all_tables_in_solution(instance_url, access_token, solution_id)
    table_logical_names = {t["LogicalName"] for t in tables}

    # 2. Build nodes
    nodes = [
        {"id": t["LogicalName"], "label": t["DisplayName"]}
        for t in tables
    ]

    # 3. Collect all relationships
    all_rels = []
    for t in tables:
        all_rels.extend(
            get_one_to_many_relationships(instance_url, access_token, t["LogicalName"])
        )
        all_rels.extend(
            get_many_to_many_relationships(instance_url, access_token, t["LogicalName"])
        )

    # 4. Deduplicate by schema_name
    seen = set()
    unique_rels = []
    for rel in all_rels:
        if rel["schema_name"] not in seen:
            seen.add(rel["schema_name"])
            unique_rels.append(rel)

    # 5. Filter to only edges where BOTH tables are in the solution
    edges = []
    for rel in unique_rels:
        if (
            rel["from_table"] in table_logical_names
            and rel["to_table"] in table_logical_names
        ):
            edge = {
                "from": rel["from_table"],
                "to": rel["to_table"],
                "type": rel["type"],
                "schema_name": rel["schema_name"],
            }
            if rel["type"] == "1:N":
                edge["from_key"] = rel.get("from_key", "")
                edge["to_key"] = rel.get("via_column", "")
                edge["via_column"] = rel.get("via_column", "")
            else:
                edge["from_key"] = rel.get("from_key", "")
                edge["to_key"] = rel.get("to_key", "")
                edge["via_table"] = rel.get("via_table", "")
            edges.append(edge)

    return {
        "nodes": nodes,
        "edges": edges,
        "solution_tables": sorted(table_logical_names),
    }
