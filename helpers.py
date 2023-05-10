import json
from datetime import datetime
from config import name, started, stopped, status, created, owner, worktime, exception, ttl


def transform_data(entity):
    entity_info = json.loads(entity)
    hr_created = hr_started = hr_stopped = "Unknown"

    if entity_info.get(created):
        hr_created = epoch_to_datetime(entity_info.get(created))
    
    if entity_info.get(started):
        hr_started = epoch_to_datetime(entity_info.get(started))
        
    if entity_info.get(stopped):
        hr_stopped = epoch_to_datetime(entity_info.get(stopped))

    return {
        "name": entity_info.get(name, "Unknown"),
        "owner": entity_info.get(owner, "Unknown"),
        "status": entity_info.get(status, "Unknown"),
        "created at": hr_created,
        "started at": hr_started,
        "stopped at": hr_stopped,
        "working time": entity_info.get(worktime, "Unknown"),
        "excepted": entity_info.get(exception, "Unknown"),
        "ttl": entity_info.get(ttl, "Unknown")
    }

def epoch_to_datetime(epoch_time_str):
    epoch_time = float(epoch_time_str)
    dt = datetime.fromtimestamp(epoch_time)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def is_expired (creation_date, ttl):
    now = datetime.utcnow().timestamp()
    if (int(now) - int(creation_date)) > int(ttl):
        return True
    
    return False
