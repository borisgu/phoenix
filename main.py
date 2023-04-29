from kubernetes import client, config
import helpers
import logging
import os

# Logging configuration
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

# Load the Kubernetes configuration from the default location
config.load_kube_config()

# Create a Kubernetes API client
api_client = client.ApiClient()

# Get the Namespace API object
api_instance = client.CoreV1Api(api_client)

# Get the Apps API object
apps_api_instance = client.AppsV1Api(api_client)

replica_sets = os.environ.get('REPLICA_SETS', 0)
label_name = os.environ.get('LABEL_NAME', 'exception')
label_value = os.environ.get('LABEL_VALUE', 'true')

def main():
    # Get the relevant namespaces
    rel_namespaces = helpers.get_namespaces(api_instance)
    
    # Get excepted namespaces
    exc_namespaces = helpers.get_excepted_namespaces(api_instance, label_name, label_value)
    logging.info("These are the excepted namespaces: {}".format(exc_namespaces))

    for ns in rel_namespaces:
        if ns not in exc_namespaces:
            deployments = helpers.get_deployments(apps_api_instance, ns)
            for dep in deployments:
                logging.info("Changing replica set in: {}".format(ns))
                helpers.change_replica_set(apps_api_instance, ns, dep, int(replica_sets))

main()