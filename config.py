import json

with open('config.json', 'r') as f:
    config = json.load(f)

# Assign configuration values
created = config['namespace_labels']['created']
stopped = config['namespace_labels']['stopped']
started = config['namespace_labels']['started']
worktime = config['namespace_labels']['worktime']
exception = config['namespace_labels']['exception']
owner = config['namespace_labels']['owner']
status = config['namespace_labels']['status']
excepted_namespaces = config['excepted_resources']['namespaces']