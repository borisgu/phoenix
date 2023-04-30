# kube-resources-controller
This small project started as a need to set replica sets to 0 to save cost in cloud provider. The idea is to go over all deployments in all deployments in all relevant namespaces and set the replica sets to 0.

There are some ignored system namespaces, like: kube-system, kube-public etc ..

## Motivation
The main motivation is to manage the cost in cloud services.
I have a scenarion where I have a fleet (100+) of developer environments where each env has a lot of deployments.
I want to scale all deployments to 0 at the end of day. So I have a scheduled job that runs this container once a day at the end of working day and scales all deployments to 0.
Since the desired state in auto scaling group is 0, all kubernetes nodes will be shut down by Karpenter or Cluster Autoscaler.

I provided a job to developers to except some namespaces if they don't want to shut down their env for some reason.
The idea is to label the namespace with some label to exclude it from scale down. This is the reason I pass the `LABEL_NAME` and `LABEL_VALUE` parameters to the container.

To build the docker image, run:
```
docker build -t some_name:some_tag .
```

To tun the docker, just run the following command:

```
docker run -d --name some_name -v ~/.kube/config:/root/.kube/config:ro -e REPLICA_SETS=0 -e LABEL_NAME=some_label -e LABEL_VALUE=some_label_value boris1580/kube-resources-ctrl:v1.0
```
We mount the `~/.kube/config` into docker container under `/root/.kube/config` as read only.

We pass some parameters used in the code, params like:
* REPLICA_SETS - number of desired replicas, default is 0
* LABEL_NAME - label for excepted namespaces, default is exception
* LABEL_VALUE - label value for excepted namespaces, default is true


