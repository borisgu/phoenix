
import datetime
import json
import helpers
from kubernetes import client, config
from config import started, stopped, created, worktime, ignored_namespaces, ttl, request_timeout, exception, kube_mode, deletion_candidate_deployment


# Load the Kubernetes configuration according to configuration in json file
if kube_mode == "incluster":
    config.load_incluster_config()
else:
    config.load_kube_config()


# Create a Kubernetes API client
api_client = client.ApiClient()
api_client.request_timeout = int(request_timeout)

# Get the Namespace API object
api_core = client.CoreV1Api(api_client)

# Get the Apps API object
api_apps = client.AppsV1Api(api_client)


def get_namespaces():
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_core.list_namespace().items

    # Declare empty list to append all workload namespaces
    workload_namespaces = []

    # Loop through each Namespace and add to list
    for namespace in all_namespaces:
        if namespace.metadata.name not in ignored_namespaces:
            workload_namespaces.append(namespace.metadata.name)
    
    return workload_namespaces

def get_namespace_details(namespace_name):
    # Get the labels for the namespace
    namespace = api_core.read_namespace(name=namespace_name)
    labels = namespace.metadata.labels

    # Convert the labels to a JSON string
    labels_json = json.dumps(labels)

    return labels_json

def get_excepted_namespaces():
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_core.list_namespace().items

    # Declare empty list to append all workload namespaces
    excepted_namespaces = []

    # Loop through each Namespace and add to new list if excepted
    for namespace in all_namespaces:

        # Get the labels of the Namespace
        labels = namespace.metadata.labels
        
        if namespace.metadata.name in ignored_namespaces:
            continue
        
        if exception in labels and labels[exception].lower() == "true":
            excepted_namespaces.append(namespace.metadata.name)
    
    return excepted_namespaces

def get_expired_namespaces():
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_core.list_namespace().items

    # Declare empty list to append all expired namespaces
    expired_namespaces = []

    # Loop through each Namespace and get its name and labels
    for namespace in all_namespaces:
        if namespace.metadata.name in ignored_namespaces:
            continue

        # Get the labels of the Namespace
        labels = namespace.metadata.labels
        
        # Check if ttl label is configured and get its value
        if labels and ttl in labels:
            # Get the ttl value and convert it to seconds
            ttl_value = int(labels[ttl]) * 24 * 60 * 60
            # Get the creation_time value
            creation_time = labels[created]
            # Check if the the namespace expired
            if helpers.is_expired(creation_time, ttl_value):
                expired_namespaces.append(namespace.metadata.name)

    return expired_namespaces

def get_deployments(namespace_name):

    deployments = []    
    # Get a list of all Deployments in the Namespace
    deployment_list = api_apps.list_namespaced_deployment(namespace_name).items

    # Loop through each Deployment and add to new list
    for dep in deployment_list:
        deployments.append(dep.metadata.name)
    
    return deployments

def get_deletion_candidate_deployment(namespace_name):
    # Since we use devspace it creates a deployment with the same name as the namespace and -devspace at the end
    # We want to delete them all and this function will help us to get the list of all deployments that we want to delete

    devspace_deployments = []
    # List deployments in the specified namespace
    deployments_list = api_apps.list_namespaced_deployment(namespace_name)

    # Iterate over the list of deployments
    for deployment in deployments_list.items:
        deployment_name = deployment.metadata.name
        # Check if the deployment name contains any string from the list
        if any(s in deployment_name for s in deletion_candidate_deployment):
            devspace_deployments.append(deployment_name)

    return devspace_deployments

def get_statefulsets(namespace_name):
    statefulsets = []
    # Get a list of StatefulSets in the specified namespace
    stateful_sets = api_apps.list_namespaced_stateful_set(namespace=namespace_name)

    # Loop through each StatefulSets and add to new list
    for stateful_set in stateful_sets.items:
        statefulsets.append(stateful_set.metadata.name)

    return statefulsets

def change_deployment_replica_set(namespace_name, deployment_name, replicas):
    # Get the Deployment object
    deployment = api_apps.read_namespaced_deployment(
        name=deployment_name,
        namespace=namespace_name
    )

    # Set the replicas count
    deployment.spec.replicas = replicas

    # Update the Deployment
    api_apps.replace_namespaced_deployment(
        name=deployment_name,
        namespace=namespace_name,
        body=deployment
    )

def change_statefulset_replica_set(namespace_name, statefulset_name, replicas):
    # Get the StatefulSet scale object
    scale = api_apps.read_namespaced_stateful_set_scale(
        name=statefulset_name,
        namespace=namespace_name
    )

    # Set the replicas count
    scale.spec.replicas = replicas

    # Update the StateFulSet
    api_apps.replace_namespaced_stateful_set_scale(
        name=statefulset_name,
        namespace=namespace_name,
        body=scale
    )

def patch_namespace_label(namespace_name, label_name, label_value):
    # Get the current labels for the namespace
    namespace = api_core.read_namespace(name=namespace_name)
    labels = namespace.metadata.labels
    
    # Add our new label, if already exists will be overriten
    labels[label_name] = str(label_value)

    # Patch the namespace with the updated labels
    body = {"metadata": {"labels": labels}}
    updated_namespace = api_core.patch_namespace(name=namespace_name, body=body)

    # Check whether the update was successful
    if updated_namespace.metadata.labels.get(label_name) == str(label_value):
        return True
    else:
        return False

def update_working_time(namespace_name):
    # Get the current labels for the namespace
    namespace = api_core.read_namespace(name=namespace_name)
    labels = namespace.metadata.labels

    # Check if working_time label already exists
    if worktime not in namespace.metadata.labels:
        created_at_value = namespace.metadata.labels.get(created)
        stopped_at_value = namespace.metadata.labels.get(stopped)
        created_time = datetime.datetime.fromtimestamp(int(created_at_value))
        stopped_time = datetime.datetime.fromtimestamp(int(stopped_at_value))
        # Calculate the working_time and convert the work_time to hours
        work_time = (stopped_time - created_time).total_seconds()/3600
        
        # Create the patch object
        labels[worktime] = str(work_time)

        # Patch the namespace with the updated labels
        body = {"metadata": {"labels": labels}}
        updated_namespace = api_core.patch_namespace(name=namespace_name, body=body)
        
        # Check whether the update was successful
        updated_namespace = api_core.patch_namespace(name=namespace_name, body=body)
        if updated_namespace.metadata.labels.get(worktime) == str(work_time):
            return True
        else:
            return False
    else:
        started_at_value = namespace.metadata.labels.get(started)
        stopped_at_value = namespace.metadata.labels.get(stopped)
        working_time_value = namespace.metadata.labels.get(worktime)
        started_time = datetime.datetime.fromtimestamp(int(started_at_value))
        stopped_time = datetime.datetime.fromtimestamp(int(stopped_at_value))
        # Calculate the working_time between started and stoppes times and convert the work_time to hours
        temp_working_time = (stopped_time - started_time).total_seconds()/3600
        # Now we sum the previous working time
        total_working_time = float(working_time_value) + float(temp_working_time)

        # Create the patch object
        labels[worktime] = str(total_working_time)

        # Patch the namespace with the updated labels
        body = {"metadata": {"labels": labels}}
        updated_namespace = api_core.patch_namespace(name=namespace_name, body=body)
        
        # Check whether the update was successful
        updated_namespace = api_core.patch_namespace(name=namespace_name, body=body)
        if updated_namespace.metadata.labels.get(worktime) == str(total_working_time):
            return True
        else:
            return False

def delete_deployment(namespace_name, deployment_name):
    # Delete the Deployment
    try:
        api_apps.delete_namespaced_deployment(name=deployment_name, namespace=namespace_name)
        return True, None
    except Exception as exception:
        return False, exception
