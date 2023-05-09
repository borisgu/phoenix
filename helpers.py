import json
from config import name, started, stopped, status, created, owner, worktime, exception


def transform_data(entity):
    entity_info = json.loads(entity)
    return {
        "name": entity_info.get(name, "Unknown"),
        "owner": entity_info.get(owner, "Unknown"),
        "status": entity_info.get(status, "Unknown"),
        "created at": entity_info.get(created, "Unknown"),
        "started at": entity_info.get(started, "Unknown"),
        "stopped at": entity_info.get(stopped, "Unknown"),
        "working time": entity_info.get(worktime, "Unknown"),
        "excepted": entity_info.get(exception, "Unknown")
    }
