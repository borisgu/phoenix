import os
import time
import kube
import helpers
import logging
import json
from flask import Flask, request, jsonify
from kubernetes import client, config
from config import started, stopped, status, max_replicas, version, app_name, timeout

application = Flask(__name__)
application.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# Logging configuration
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


# Load the Kubernetes configuration from the defa   ult location
config.load_kube_config()

# Create a Kubernetes API client
api_client = client.ApiClient(timeout_seconds=timeout)

# Get the Namespace API object
api_core = client.CoreV1Api(api_client)

# Get the Apps API object
api_apps = client.AppsV1Api(api_client)

# Get app version
@ application.route('/version', methods=['GET'])
def get_app_version():
    """App version information"""
    return jsonify({'name': app_name, "version": version}), 200

# Get a list of all namespaces
@application.route('/namespaces/all', methods=['GET'])
def get_namespaces():
    logging.info("Getting all namespaces")
    all_namespaces = kube.get_namespaces(api_core)
    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404

    return jsonify({'namespaces': all_namespaces}), 200


# Get a list of all namespaces
@application.route('/report', methods=['GET'])
def get_detailed_report():
    logging.info("Generating report")
    all_namespaces = kube.get_namespaces(api_core)
    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404
    
    data = []
    for namespace in all_namespaces:
        ns_info = kube.get_namespace_details(api_core, namespace)
        data.append(helpers.transform_data(ns_info))

    return jsonify({'report': data}), 200

# Get a list of all excepted namespaces by prividing the label and value in URL
# For Example:
# http://127.0.0.1:5001/namespaces/excepted?label=exception&value=true
@application.route('/namespaces/excepted', methods=['GET'])
def get_excepted_namespaces():
    label = request.args.get('label')
    value = request.args.get('value')
    if not label:
        return jsonify({'error': 'label parameter is required'}), 400
    elif not value:
        return jsonify({'error': 'value parameter is required'}), 400
    logging.info("Getting all excepted namespaces")
    excepted_namespaces = kube.get_excepted_namespaces(api_core, label, value)
    if not excepted_namespaces:
        return jsonify({'message': 'no excepted namespaces found'}), 404
    
    # timestamp = int(time.time())

    #return jsonify({'namespaces': excepted_namespaces, 'time': timestamp}), 200
    return jsonify({'namespaces': excepted_namespaces}), 200


# Scale up/down not excepted namespaces
@application.route('/scale', methods=['POST'])
def set_scale_operation():
    limited = False
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Request body must be a JSON object'}), 400
    
    replicas = data.get("replicas")
    namespace = data.get("namespace")
    if int(replicas) < 0:
        return jsonify({'error': 'Value of replicas must be 0 or above'}), 400
    
    # We limit the number of replicas to 1
    if int(replicas) > max_replicas:
        limited = True
        replicas = max_replicas

    # Check if the namespace exists
    if namespace not in kube.get_namespaces(api_core):
        return jsonify({'info': 'namespace {} does not exist'.format(namespace)}), 400
    
    # Get all namespaces labels for future use
    ns_labels = json.loads(kube.get_namespace_details(api_core, namespace))
    if status not in ns_labels:
        logging.info("It's the first time this namespace manipulated\n Going to label the namespace with {}=up label".format(status))
        kube.patch_namespace_label(api_core, namespace, status, "up")
        # Now we need to reload the new labels
        ns_labels = json.loads(kube.get_namespace_details(api_core, namespace))
    
    if ns_labels[status] == "down" and int(replicas) == 0:
        return jsonify({'message': 'ENV {} is already down'.format(namespace)}), 200
    
    if ns_labels[status] == "up" and int(replicas) > 0:
        return jsonify({'message': 'ENV {} is already up'.format(namespace)}), 200

    # Get all deployments in relevant namespace
    deployments = kube.get_deployments(api_apps, namespace)
    # Set all deployments to relevant replica number
    for deploy in deployments:
        logging.info("Changing replica set in: {ns} to {num}".format(ns=namespace, num=replicas))
        kube.change_deployment_replica_set(api_apps, namespace, deploy, int(replicas))
    
    # Now we need to set a label with the time we patched the deployments in the relevant namespace
    timestamp = int(time.time())
    if int(replicas) == 0:
        patch_time_result = kube.patch_namespace_label(api_core, namespace, stopped, timestamp)
        patch_status_result = kube.patch_namespace_label(api_core, namespace, status, "down")
        # Update working_time label
        kube.update_working_time(api_core, namespace)

    elif int(replicas) > 0:
        patch_time_result = kube.patch_namespace_label(api_core, namespace, started, timestamp)
        patch_status_result = kube.patch_namespace_label(api_core, namespace, status, "up")

    if patch_time_result and patch_status_result and limited:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas), 'message': 'Replicas limited to 1'}), 200
    
    if patch_time_result and patch_status_result:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas)}), 200
    

if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT,
                    debug=ENVIRONMENT_DEBUG)
