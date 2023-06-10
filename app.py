import os
import time
import kube
import helpers
import logging
import json
from flask import Flask, request, jsonify
from config import started, stopped, status, max_replicas, version, app_name

application = Flask(__name__)
application.config['JSONIFY_PRETTYPRINT_REGULAR'] = True


# Logging configuration
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')


# Get app version
@ application.route('/version', methods=['GET'])
def get_app_version():
    """App version information"""
    return jsonify({'name': app_name, "version": version}), 200

# Get a list of all namespaces
@application.route('/namespaces/all', methods=['GET'])
def get_namespaces():
    logging.info("Getting all namespaces")
    all_namespaces = kube.get_namespaces()
    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404

    return jsonify({'namespaces': all_namespaces}), 200


# Get a list of all namespaces
@application.route('/report', methods=['GET'])
def get_detailed_report():
    logging.info("Generating report")
    all_namespaces = kube.get_namespaces()
    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404
    
    data = []
    for namespace in all_namespaces:
        ns_info = kube.get_namespace_details(namespace)
        data.append(helpers.transform_data(ns_info))

    return jsonify({'report': data}), 200

# Get a list of all excepted namespaces by prividing the label and value in URL
# For Example:
# http://127.0.0.1:5001/namespaces/excepted?label=exception&value=true
@application.route('/namespaces/excepted', methods=['GET'])
def get_excepted_namespaces():
    logging.info("Getting all excepted namespaces")
    excepted_namespaces = kube.get_excepted_namespaces()
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
    force_scale = data.get("force", "false")
    
    if not replicas or int(replicas) < 0:
        return jsonify({'error': 'Value of replicas must be 0 or above'}), 400
    
    # Check if the namespace is excepted
    excepted_namespaces = kube.get_excepted_namespaces()
    if int(replicas) == 0 and namespace in excepted_namespaces and force_scale == "false":
        logging.info("Namespace {} is excepted and cannot be scaled down".format(namespace))
        return jsonify({'blocked': "namespace excepted"})
    
    # We limit the number of replicas to 1
    if int(replicas) > int(max_replicas):
        limited = True
        replicas = max_replicas

    # Check if the namespace exists
    if namespace not in kube.get_namespaces():
        return jsonify({'info': 'namespace {} does not exist'.format(namespace)}), 400
    
    # Get all namespaces labels for future use
    ns_labels = json.loads(kube.get_namespace_details(namespace))
    if status not in ns_labels:
        logging.info("It's the first time this namespace manipulated\n Going to label the namespace with {}=up label".format(status))
        kube.patch_namespace_label(namespace, status, "up")
        # Now we need to reload the new labels
        ns_labels = json.loads(kube.get_namespace_details(namespace))
    
    if ns_labels[status] == "down" and int(replicas) == 0:
        return jsonify({'message': 'ENV {} is already down'.format(namespace)}), 200
    
    if ns_labels[status] == "up" and int(replicas) > 0:
        return jsonify({'message': 'ENV {} is already up'.format(namespace)}), 200

    # Get all deployments and statefulsets in relevant namespace
    deployments = kube.get_deployments(namespace)
    statefulsets = kube.get_statefulsets(namespace)

    # Set all deployments to relevant replica number
    for deploy in deployments:
        logging.info("Changing deployment replica set in: {ns} to {num}".format(ns=namespace, num=replicas))
        kube.change_deployment_replica_set(namespace, deploy, int(replicas))
    
    # Set all statefulsets to relevant replica number
    for statefulset in statefulsets:
        logging.info("Changing statefulset replica set in: {ns} to {num}".format(ns=namespace, num=replicas))
        kube.change_statefulset_replica_set(namespace, statefulset, int(replicas))

    # Now we need to set a label with the time we patched the deployments in the relevant namespace
    timestamp = int(time.time())
    if int(replicas) == 0:
        patch_time_result = kube.patch_namespace_label(namespace, stopped, timestamp)
        patch_status_result = kube.patch_namespace_label(namespace, status, "down")
        # Update working_time label
        kube.update_working_time(namespace)

    elif int(replicas) > 0:
        patch_time_result = kube.patch_namespace_label(namespace, started, timestamp)
        patch_status_result = kube.patch_namespace_label(namespace, status, "up")

    if patch_time_result and patch_status_result and limited:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas), 'message': 'Replicas limited to 1'}), 200
    
    if patch_time_result and patch_status_result:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas)}), 200


# Get a list of expired namespaces
@application.route('/namespaces/expired', methods=['GET'])
def get_expired_namespaces():
    logging.info("Getting all expired namespaces")
    all_namespaces = kube.get_namespaces()
    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404

    # Get all expired namespaces
    expired_namespaces = kube.get_expired_namespaces()

    if not expired_namespaces:
        return jsonify({'message': 'no expired namespaces found'}), 404

    return jsonify({'namespaces': expired_namespaces}), 200

if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5001)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT,
                    debug=ENVIRONMENT_DEBUG)
