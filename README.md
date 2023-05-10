# Phoenix
This small project started as a need to set replica sets to 0 to save cost in cloud provider. The idea is to go over all deployments in all deployments in all relevant namespaces and set the replica sets to 0.

There are some ignored system namespaces, like: kube-system, kube-public etc .. (see in config.json file)

## Motivation
The main motivation is to manage the cost in cloud services.
I have a scenarion where I have a fleet (100+) of developer environments where each env has a lot of deployments.

I want to scale all deployments to 0 at the end of day. So I have a scheduled job that sends scale down REST api to this app and scales all but excepted namespaces at the end of working day.
Since the desired state in auto scaling group is 0, all kubernetes nodes will be shut down by Karpenter or Cluster Autoscaler.

I provided a job to developers to except some namespaces if they don't want to shut down their env for some reason.
The idea is to label the namespace with some label to exclude it from scale down.
The labels are configurable throuth the `config.json` file.

The idea is not running some database and use labels on the namespaces. This way this up is stateless and can be restarted or re-deployed somewhere else.

By default we create ENV with ttl label set to 30 (days). There is a job that sends REST api to `/namespaces/expired` endpoint. Once called, this will go over all namespaces and check the ttl, if expired it will return a JSON response with a list of all expired namespaces.

If the developer want to extend the expiration time, he can send a request and extend it. (Check the relevant REST api to do it)

---
### Build and Use

To build the docker image, run:

```
docker build -t some_name:some_tag .
```

To tun the docker, just run the following command:

```
docker run -d --name some_name -v ~/.kube/config:/home/www/.kube/config:ro -v ./config.json:/var/www/config.json:ro -e AWS_ACCESS_KEY_ID=your_aws_access_key -e AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key boris1580/phoenix:v1.1.0
```
We mount the `~/.kube/config` into docker container under `/www/.kube/config` as read only.
We need to pass AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in case we use EKS oidc based access.
In addition we mount the `config.json` file into `/var/www/config.json` as read only as well.

**Note:**

These two mounts are mandatory, the app will not start without them

---
Example of `config.json`:

```
{
    "namespace_labels": {
        "name": "kubernetes.io/metadata.name",
        "started": "started_at",
        "stopped": "stopped_at",
        "created": "created_at",
        "worktime": "working_time",
        "exception": "exception",
        "owner": "owner",
        "status": "status",
        "ttl": "ttl"
    },
    "excepted_resources": {
        "namespaces": ["kube-system","kube-public","kube-flannel","kube-node-lease","envoy-gateway-system","gateway-system","karpenter","nginx-gateway","ops"]
    },
    "resources_limits": {
        "max_pod_replicas": "1"
    },
    "app_info": {
        "name": "Phoenix",
        "version": "1.1.0"
    },
    "kube_api_config": {
        "request_timeout": 120
    }
}
````


### Current capabilities and commands:


1. Get all namespaces: 

```
curl http://127.0.0.1:5001/namespaces/all
```

Gets all namespaces except the `excepted_resources.namespaces` in config.json.

2. Get excepted namespaces:

```
curl http://127.0.0.1:5001/namespaces/excepted
```

Gets all excepted namespaces. The `exception` label is configured in config.json.

3. Get all expired namespaces: 

```
curl http://127.0.0.1:5001/namespaces/expired
```

Gets all expired namespaces except the `excepted_resources.namespaces` in config.json.

3. Scale deployments up/down:

```
curl -X POST 'http://127.0.0.1:5001/scale' \
--header 'Content-Type: application/json' \
--data '{
    "namespace": "helloworld",
    "replicas": "0"
}
```
It goes over all deployments in `helloworld` namespace and sets replicas to 0.
If you send 1, it will obviously set all replicas to 1 but, if you send morethan 1 the replica number still will be set to 1. This is limited in `config.json` under `resources_limits.max_pod_replicas`.

4. Get report:

```
curl 'http://127.0.0.1:5001/report'
```

It will go over all namespaces in the cluster and get you all labels in JSON format.

5. Get app version:

```
curl 'http://127.0.0.1:5001/version'
```
Returns you the app name and the version. Both parameters configured in `config.json` under `app_info`.

---
