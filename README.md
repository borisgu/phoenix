# kube-resources-controller
This small project started as a need to set replica sets to 0 to save cost in cloud provider.

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


