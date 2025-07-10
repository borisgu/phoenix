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


# Get a list of all namespaces (local or remote)
@application.route('/namespaces/all', methods=['GET', 'POST'])
def get_namespaces():
    logging.info("Getting all namespaces")
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args or {}
    context = data.get('context')
    role_arn = data.get('role_arn')
    region_name = data.get('region_name')

    if context and role_arn:
        api_core, _ = kube.setup_kube_for_api(context=context, role_arn=role_arn, region_name=region_name)
        all_namespaces = [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces]
    else:
        all_namespaces = kube.get_namespaces()

    if not all_namespaces:
        return jsonify({'message': 'no namespaces found'}), 404
    return jsonify({'namespaces': all_namespaces}), 200



# Get a list of all namespaces with details (local or remote)
@application.route('/report', methods=['GET', 'POST'])
def get_detailed_report():
    logging.info("Generating report")
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args or {}
    context = data.get('context')
    role_arn = data.get('role_arn')
    region_name = data.get('region_name')

    if context and role_arn:
        api_core, _ = kube.setup_kube_for_api(context=context, role_arn=role_arn, region_name=region_name)
        all_namespaces = [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces]
        def get_ns_info(ns):
            ns_obj = api_core.read_namespace(name=ns)
            labels = ns_obj.metadata.labels
            return helpers.transform_data(json.dumps(labels))
        data_report = [get_ns_info(ns) for ns in all_namespaces]
    else:
        all_namespaces = kube.get_namespaces()
        if not all_namespaces:
            return jsonify({'message': 'no namespaces found'}), 404
        data_report = []
        for namespace in all_namespaces:
            ns_info = kube.get_namespace_details(namespace)
            data_report.append(helpers.transform_data(ns_info))

    return jsonify({'report': data_report}), 200


# Get a list of all excepted namespaces (local or remote)
@application.route('/namespaces/excepted', methods=['GET', 'POST'])
def get_excepted_namespaces():
    logging.info("Getting all excepted namespaces")
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args or {}
    context = data.get('context')
    role_arn = data.get('role_arn')
    region_name = data.get('region_name')

    if context and role_arn:
        api_core, _ = kube.setup_kube_for_api(context=context, role_arn=role_arn, region_name=region_name)
        all_namespaces = [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces]
        excepted_namespaces = []
        for ns in all_namespaces:
            ns_obj = api_core.read_namespace(name=ns)
            labels = ns_obj.metadata.labels or {}
            if kube.exception in labels and labels[kube.exception].lower() == "true":
                excepted_namespaces.append(ns)
    else:
        excepted_namespaces = kube.get_excepted_namespaces()

    if not excepted_namespaces:
        return jsonify({'message': 'no excepted namespaces found'}), 404
    return jsonify({'namespaces': excepted_namespaces}), 200



# Scale up/down not excepted namespaces (local or remote)
@application.route('/scale', methods=['POST'])
def set_scale_operation():
    limited = False
    data = request.get_json() or {}
    context = data.get('context')
    role_arn = data.get('role_arn')
    region_name = data.get('region_name')

    replicas = data.get("replicas")
    namespace = data.get("namespace")
    force_scale = data.get("force", "false")
    delete_deploy = data.get("delete_deploy", "false")

    # Use remote or local kube clients
    if context and role_arn:
        api_core, api_apps = kube.setup_kube_for_api(context=context, role_arn=role_arn, region_name=region_name)
        # Helper lambdas for remote
        get_excepted_namespaces = lambda: [ns for ns in [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces] if (api_core.read_namespace(name=ns).metadata.labels or {}).get(kube.exception, '').lower() == 'true']
        get_namespaces = lambda: [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces]
        get_namespace_details = lambda ns: json.dumps(api_core.read_namespace(name=ns).metadata.labels or {})
        get_deployments = lambda ns: [dep.metadata.name for dep in api_apps.list_namespaced_deployment(ns).items]
        get_statefulsets = lambda ns: [ss.metadata.name for ss in api_apps.list_namespaced_stateful_set(namespace=ns).items]
        patch_namespace_label = lambda ns, label, value: api_core.patch_namespace(name=ns, body={"metadata": {"labels": {label: str(value)}}})
        change_deployment_replica_set = lambda ns, dep, rep: api_apps.patch_namespaced_deployment_scale(name=dep, namespace=ns, body={"spec": {"replicas": rep}})
        change_statefulset_replica_set = lambda ns, ss, rep: api_apps.patch_namespaced_stateful_set_scale(name=ss, namespace=ns, body={"spec": {"replicas": rep}})
        # For deletion, fallback to local logic (or implement remote if needed)
        get_deletion_candidate_deployment = lambda ns: [dep.metadata.name for dep in api_apps.list_namespaced_deployment(ns).items if any(s in dep.metadata.name for s in kube.deletion_candidate_deployment)]
        update_working_time = lambda ns: True  # Not implemented for remote
    else:
        get_excepted_namespaces = kube.get_excepted_namespaces
        get_namespaces = kube.get_namespaces
        get_namespace_details = kube.get_namespace_details
        get_deployments = kube.get_deployments
        get_statefulsets = kube.get_statefulsets
        patch_namespace_label = kube.patch_namespace_label
        change_deployment_replica_set = kube.change_deployment_replica_set
        change_statefulset_replica_set = kube.change_statefulset_replica_set
        get_deletion_candidate_deployment = kube.get_deletion_candidate_deployment
        update_working_time = kube.update_working_time

    if delete_deploy == "true":
        deployments = get_deletion_candidate_deployment(namespace)
        logging.info("Going to delete deployment {} in namespace: {}".format(deployments, namespace))
        for deploy in deployments:
            # Only works for local for now
            delete_result = kube.delete_deployment(namespace, deploy)
            if not delete_result:
                return jsonify({'error': 'Deployment {} could not be deleted in namespace {}'.format(deploy, namespace)}), 400
            logging.info("Deployment {} deleted in namespace {}".format(deploy, namespace))

    if not replicas or int(replicas) < 0:
        return jsonify({'error': 'Value of replicas must be 0 or above'}), 400

    excepted_namespaces = get_excepted_namespaces()
    if int(replicas) == 0 and namespace in excepted_namespaces and force_scale == "false":
        logging.info("Namespace {} is excepted and cannot be scaled down".format(namespace))
        return jsonify({'blocked': "namespace excepted"})

    if int(replicas) > int(max_replicas):
        limited = True
        replicas = max_replicas

    if namespace not in get_namespaces():
        return jsonify({'info': 'namespace {} does not exist'.format(namespace)}), 400

    ns_labels = json.loads(get_namespace_details(namespace))
    if status not in ns_labels:
        logging.info("It's the first time this namespace manipulated\n Going to label the namespace with {}=up label".format(status))
        patch_namespace_label(namespace, status, "up")
        ns_labels = json.loads(get_namespace_details(namespace))

    if ns_labels[status] == "down" and int(replicas) == 0:
        return jsonify({'message': 'ENV {} is already down'.format(namespace)}), 200

    if ns_labels[status] == "up" and int(replicas) > 0:
        return jsonify({'message': 'ENV {} is already up'.format(namespace)}), 200

    deployments = get_deployments(namespace)
    statefulsets = get_statefulsets(namespace)

    for deploy in deployments:
        logging.info("Changing deployment replica set in: {ns} to {num}".format(ns=namespace, num=replicas))
        change_deployment_replica_set(namespace, deploy, int(replicas))

    for statefulset in statefulsets:
        logging.info("Changing statefulset replica set in: {ns} to {num}".format(ns=namespace, num=replicas))
        change_statefulset_replica_set(namespace, statefulset, int(replicas))

    timestamp = int(time.time())
    if int(replicas) == 0:
        patch_time_result = patch_namespace_label(namespace, stopped, timestamp)
        patch_status_result = patch_namespace_label(namespace, status, "down")
        update_working_time(namespace)
    elif int(replicas) > 0:
        patch_time_result = patch_namespace_label(namespace, started, timestamp)
        patch_status_result = patch_namespace_label(namespace, status, "up")

    if patch_time_result and patch_status_result and limited:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas), 'message': 'Replicas limited to 1'}), 200

    if patch_time_result and patch_status_result:
        return jsonify({'info': 'All deployments in {ns} scaled to {rep}'.format(ns=namespace, rep=replicas)}), 200



# Get a list of expired namespaces (local or remote)
@application.route('/namespaces/expired', methods=['GET', 'POST'])
def get_expired_namespaces():
    logging.info("Getting all expired namespaces")
    if request.method == 'POST':
        data = request.get_json() or {}
    else:
        data = request.args or {}
    context = data.get('context')
    role_arn = data.get('role_arn')
    region_name = data.get('region_name')

    if context and role_arn:
        api_core, _ = kube.setup_kube_for_api(context=context, role_arn=role_arn, region_name=region_name)
        all_namespaces = [ns.metadata.name for ns in api_core.list_namespace().items if ns.metadata.name not in kube.ignored_namespaces]
        expired_namespaces = []
        for ns in all_namespaces:
            ns_obj = api_core.read_namespace(name=ns)
            labels = ns_obj.metadata.labels or {}
            if labels and kube.ttl in labels:
                ttl_value = int(labels[kube.ttl]) * 24 * 60 * 60
                creation_time = labels[kube.created]
                if helpers.is_expired(creation_time, ttl_value):
                    expired_namespaces.append(ns)
    else:
        all_namespaces = kube.get_namespaces()
        if not all_namespaces:
            return jsonify({'message': 'no namespaces found'}), 404
        expired_namespaces = kube.get_expired_namespaces()

    if not expired_namespaces:
        return jsonify({'message': 'no expired namespaces found'}), 404
    return jsonify({'namespaces': expired_namespaces}), 200

if __name__ == "__main__":
    ENVIRONMENT_DEBUG = os.environ.get("APP_DEBUG", True)
    ENVIRONMENT_PORT = os.environ.get("APP_PORT", 5000)
    application.run(host='0.0.0.0', port=ENVIRONMENT_PORT,
                    debug=ENVIRONMENT_DEBUG)
