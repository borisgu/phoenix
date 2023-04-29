
IGNORED_NAMESPACES=['kube-system','kube-public','kube-flannel','kube-node-lease']

def get_namespaces(api_instance):
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_instance.list_namespace().items

    # Declare empty list to append all workload namespaces
    workload_namespaces = []

    # Loop through each Namespace and print its name and labels
    for ns in all_namespaces:
        if ns.metadata.name not in IGNORED_NAMESPACES:
            # print("Namespace: {}".format(ns.metadata.name))
            # print("Labels: {}".format(ns.metadata.labels))
            # print("\n")
            workload_namespaces.append(ns.metadata.name)
    
    return workload_namespaces


def get_excepted_namespaces(api_instance, label_name, label_value):
    # Get a list of all Namespaces in the cluster
    all_namespaces = api_instance.list_namespace().items

    # Declare empty list to append all workload namespace
    excepted_namespaces = []

    # Loop through each Namespace and print its name and labels
    for ns in all_namespaces:
        # Get the Namespace object
        api_instance.read_namespace(ns.metadata.name)

        # Get the labels of the Namespace
        labels = ns.metadata.labels
        
        if ns.metadata.name in IGNORED_NAMESPACES:
            continue
        
        if label_name in labels and labels[label_name].lower() == label_value:
            excepted_namespaces.append(ns.metadata.name)
    
    return excepted_namespaces


def get_deployments(api_instance, namespace):

    deployments = []    
    # Get a list of all Deployments in the Namespace
    deployment_list = api_instance.list_namespaced_deployment(namespace).items

    # Loop through each Deployment and print its name
    for dep in deployment_list:
        # print("Deployments in {ns}: {deployment}".format(deployment=dep.metadata.name, ns=namespace))
        # print("\n")
        deployments.append(dep.metadata.name)
    
    return deployments

def change_replica_set(api_instance, namespace, deployment_name, replicas):
    # Get the Deployment object
    deployment = api_instance.read_namespaced_deployment(
        name=deployment_name,
        namespace=namespace
    )

    # Set the replicas count
    deployment.spec.replicas = replicas

    # Update the Deployment
    api_instance.replace_namespaced_deployment(
        name=deployment_name,
        namespace=namespace,
        body=deployment
    )
