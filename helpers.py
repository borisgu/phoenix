
import datetime
import json
from config import started, stopped, created, worktime, excepted_namespaces


def get_namespaces(api_instance):
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_instance.list_namespace().items

    # Declare empty list to append all workload namespaces
    workload_namespaces = []

    # Loop through each Namespace and print its name and labels
    for ns in all_namespaces:
        if ns.metadata.name not in excepted_namespaces:
            # print("Namespace: {}".format(ns.metadata.name))
            # print("Labels: {}".format(ns.metadata.labels))
            # print("\n")
            workload_namespaces.append(ns.metadata.name)
    
    return workload_namespaces

def get_namespace_details(api, namespace_name):
    # Get the labels for the namespace
    namespace = api.read_namespace(name=namespace_name)
    labels = namespace.metadata.labels

    # Convert the labels to a JSON string
    labels_json = json.dumps(labels)

    return labels_json


def get_excepted_namespaces(api, label_name, label_value):
    # Get a list of all Namespaces in the cluster
    all_namespaces = api.list_namespace().items

    # Declare empty list to append all workload namespace
    excepted_namespaces = []

    # Loop through each Namespace and print its name and labels
    for ns in all_namespaces:
        # Get the Namespace object
        api.read_namespace(ns.metadata.name)

        # Get the labels of the Namespace
        labels = ns.metadata.labels
        
        if ns.metadata.name in excepted_namespaces:
            continue
        
        if label_name in labels and labels[label_name].lower() == label_value:
            excepted_namespaces.append(ns.metadata.name)
    
    return excepted_namespaces


def get_deployments(api, namespace):

    deployments = []    
    # Get a list of all Deployments in the Namespace
    deployment_list = api.list_namespaced_deployment(namespace).items

    # Loop through each Deployment and print its name
    for dep in deployment_list:
        # print("Deployments in {ns}: {deployment}".format(deployment=dep.metadata.name, ns=namespace))
        # print("\n")
        deployments.append(dep.metadata.name)
    
    return deployments

def change_replica_set(api, namespace, deployment_name, replicas):
    # Get the Deployment object
    deployment = api.read_namespaced_deployment(
        name=deployment_name,
        namespace=namespace
    )

    # Set the replicas count
    deployment.spec.replicas = replicas

    # Update the Deployment
    api.replace_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )

def patch_namespace_label(api, namespace_name, label_name, label_value):
    # Get the current labels for the namespace
    namespace = api.read_namespace(name=namespace_name)
    labels = namespace.metadata.labels
    
    # Add our new label, if already exists will be overriten
    labels[label_name] = str(label_value)

    # Patch the namespace with the updated labels
    body = {"metadata": {"labels": labels}}
    print("These are the labels: " + str(body))
    updated_namespace = api.patch_namespace(name=namespace_name, body=body)

    # Check whether the update was successful
    print("Checking that the patch applied")
    if updated_namespace.metadata.labels.get(label_name) == str(label_value):
        print("{} label patch applied successfully".format(label_name))
        return True
    else:
        print("{} label patch not applied".format(label_name))
        return False

def update_working_time(api, namespace_name):
    # Get the current labels for the namespace
    namespace = api.read_namespace(name=namespace_name)
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
        print("These are the labels: " + str(body))
        updated_namespace = api.patch_namespace(name=namespace_name, body=body)
        
        # Check whether the update was successful
        print("Checking that the working_time patch applied")
        updated_namespace = api.patch_namespace(name=namespace_name, body=body)
        if updated_namespace.metadata.labels.get(worktime) == str(work_time):
            print("working_time patch applied successfully")
            return True
        else:
            print("working_time patch not applied")
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
        print("This is the calculated total working time - {}".format(total_working_time))

        # Create the patch object
        labels[worktime] = str(total_working_time)

        # Patch the namespace with the updated labels
        body = {"metadata": {"labels": labels}}
        print("These are the labels: " + str(body))
        updated_namespace = api.patch_namespace(name=namespace_name, body=body)
        
        # Check whether the update was successful
        print("Checking that the total working_time patch applied")
        updated_namespace = api.patch_namespace(name=namespace_name, body=body)
        if updated_namespace.metadata.labels.get(worktime) == str(total_working_time):
            print("working_time patch applied successfully")
            return True
        else:
            print("working_time patch not applied")
            return False

def epoch_to_dhm(epoch_time):
    # Convert epoch time to a datetime object
    dt = datetime.datetime.fromtimestamp(epoch_time)
    # Calculate the difference between the datetime object and the epoch time
    td = datetime.datetime.utcnow() - dt
    # Extract the number of days, hours, and minutes from the time difference
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    # Return the result as a tuple
    return days, hours, minutes