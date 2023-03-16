#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#
import argparse
import glob
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml
from jinja2 import Template

TARGET_NAMESPACE_LABEL = os.getenv("LABEL", "user.kubeflow.org/enabled")
TEMPLATES_FOLDER = os.getenv("TEMPLATES_FOLDER", "./resources")
PORT = os.getenv("PORT", 80)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def main(port: int, label: str, folder: str) -> None:
    """
    Runs a server for injecting resources into namespaces by given label
    """
    logger.info("Resource dyspatcher service alive")
    server = server_factory(port, label, folder)
    logger.info("Serving forever")
    server.serve_forever()


def server_factory(controller_port: int, label: str, folder: str, url: str = "") -> HTTPServer:
    """
    Returns an HTTPServer populated with Handler with customized settings
    """

    class Controller(BaseHTTPRequestHandler):
        def sync(self, parent, children):
            logger.info("Got new request")
            context = {"namespace": parent.get("metadata", {}).get("name")}
            pipeline_enabled = parent.get("metadata", {}).get("labels", {}).get(label)

            if pipeline_enabled != "true":
                logger.info(
                    f"Namespace not in scope, no action taken (metadata.labels.{label} = {pipeline_enabled}, must be 'true')"  # noqa: E501
                )
                return {"status": {}, "children": []}

            desired_secret_count = 0
            desired_resources = []
            desired_status = {
                "resources-ready": len(children["Secret.v1"]) == desired_secret_count
                and "True"
                or "False"
            }

            desired_resources += generate_manifests(folder, context)
            return {"status": desired_status, "children": desired_resources}

        def do_POST(self):  # noqa: N802
            """
            Serve the sync() function as a JSON webhook
            """
            observed = json.loads(self.rfile.read(int(self.headers.get("content-length"))))
            desired = self.sync(observed["parent"], observed["children"])

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(json.dumps(desired), "utf-8"))

    return HTTPServer((url, int(controller_port)), Controller)


def generate_manifests(templates_folder: str, context: dict) -> list[dict]:
    """
    For each file in templates_folder generate a yaml with populated context
    """
    template_files = glob.glob(f"{templates_folder}/*.j2")
    manifests = []
    for template_file in template_files:
        template = Template(Path(template_file).read_text())
        rendered_template = template.render(**context)
        tmp_yaml = yaml.safe_load(rendered_template)
        manifests.append(tmp_yaml)
    return manifests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port on which run the sync server",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--label",
        "-l",
        type=str,
        help="Namespace label to which should be the resources injected",
        default=None,
        required=False,
    )
    parser.add_argument(
        "--folder",
        "-f",
        type=str,
        help="Folder wehre resource templates should be stored",
        default=None,
        required=False,
    )
    args = parser.parse_args()
    port = args.port or PORT
    label = args.label or TARGET_NAMESPACE_LABEL
    folder = args.folder or TEMPLATES_FOLDER
    main(port, label, folder)
