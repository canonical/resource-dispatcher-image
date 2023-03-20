#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#

"""Integration tests for Resource Dispatcher server controller."""

import json
import threading
from http.server import HTTPServer

import pytest
import requests

from src.server import server_factory

PORT = 0  # HTTPServer randomly assigns the port to a free port
LABEL = "test.label"
FOLDER = "./tests/test_data_folder"

CORRECT_NAMESPACE_REQ = {
    "parent": {"metadata": {"name": "someName", "labels": {LABEL: "true"}}},
    "children": {
        "Secret.v1": [],
        "ConfigMap.v1": [],
        "Deployment.apps/v1": [],
        "Service.v1": [],
    },
}

WRONG_NAMESPACE_REQ = {
    "parent": {"metadata": {"name": "someName", "labels": {"wrong.namespace": "true"}}},
    "children": {
        "Secret.v1": [],
        "ConfigMap.v1": [],
        "Deployment.apps/v1": [],
        "Service.v1": [],
    },
}

CORRECT_NAMESPACE_RESP = {
    "status": {"resources-ready": "False"},
    "children": [
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "mlpipeline-minio-artifact2", "namespace": "someName"},
            "stringData": {"AWS_ACCESS_KEY_ID": "value", "AWS_SECRET_ACCESS_KEY": "value"},
        },
        {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": {"name": "mlpipeline-minio-artifact", "namespace": "someName"},
            "stringData": {"AWS_ACCESS_KEY_ID": "value", "AWS_SECRET_ACCESS_KEY": "value"},
        },
    ],
}

WRONG_NAMESPACE_RESP = {"status": {}, "children": []}


@pytest.fixture(
    scope="function",
)
def server():
    """
    Start the sync HTTP server for a given set of parameters. Create server on a separate thread.

    Yields:
    * the server (useful to interrogate for the server address)
    """
    server = server_factory(PORT, LABEL, FOLDER)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    yield server


@pytest.mark.parametrize(
    "request_data, response_data",
    [
        (CORRECT_NAMESPACE_REQ, CORRECT_NAMESPACE_RESP),
        (WRONG_NAMESPACE_REQ, WRONG_NAMESPACE_RESP),
    ],
)
def test_server_responses(server: HTTPServer, request_data, response_data):
    """Test if server returns desired Kubernetes objects for given namespaces."""
    server_obj = server
    url = f"http://{server_obj.server_address[0]}:{str(server_obj.server_address[1])}"
    print("url: ", url)
    print("data")
    print(json.dumps(request_data))
    x = requests.post(url, data=json.dumps(request_data))
    result = json.loads(x.text)
    assert result["status"] == response_data["status"]
    assert all([a == b for a, b in zip(result["children"], response_data["children"])])
