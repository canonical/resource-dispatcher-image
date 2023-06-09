# Resource dispatcher Docker image
This repository contains an image with an HTTP server that should be used in the Kubernetes meta-controller charm called [resource-dispatcher](https://github.com/canonical/resource-dispatcher). For each GET request on the /sync path, the resource dispatcher will generate Kubernetes manifests that need to be injected into the given Kubernetes namespace. Information about the Kubernetes namespace should be included in the body of the request. Here is an example of a JSON body:

```
{
    "parent": {
        "metadata": {
            "name": "someName",
            "labels": {
                "user.kubeflow.org/enabled": "true"
            }
        }
    },
    "children": {
        "Secret.v1": [],
    }
}
```

For the given request, we see information about the `someName` namespace, which currently does not have any secrets in it.

To determine which resource will be created for each request, the server uses a folder with templates. On each request, each of these templates will be rendered and provided. The content of the folder may be changed and configured.

To run the server, you can use the Docker image which you can find [here](https://hub.docker.com/r/charmedkubeflow/resource-dispatcher/tags). To run the dispatcher, use the following Docker run command:

```
docker run -p 80:80  charmedkubeflow/resource-dispatcher:<tag>
```

The configuration of the server can be overridden by specifying the following parameters for resource_dispatcher/main.py:

- `--port -p (env. PORT)` to specify on which port the dispatcher server will run (default 80)
- `--label -l (env. TARGET_NAMESPACE_LABEL)` to specify for which namespace label the resources will be injected (default user.kubeflow.org/enabled)
- `--folder -f (env. TEMPLATES_FOLDER)` to specify the location of the templates folder to serve
