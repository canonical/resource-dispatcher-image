#!/usr/bin/env python3
# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
#

"""Run HTTPServer for Resource Dispatcher."""

import glob
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import yaml
from jinja2 import Template

from .log import setup_custom_logger

logger = setup_custom_logger("server")


def run_server(port: int, label: str, folder: str) -> None:
    """Run a server for injecting resources into namespaces by given label."""
    logger.info("Resource dispatcher service alive")
    server = server_factory(port, label, folder)
    logger.info(
        f"Serving sync server forever on port: {port}, for label: {label}, on folder: {folder}"
    )
    server.serve_forever()


def server_factory(controller_port: int, label: str, folder: str, url: str = "") -> HTTPServer:
    """Return an HTTPServer populated with Handler with customised settings."""

    class Controller(BaseHTTPRequestHandler):
        def sync(self, parent, children):
            """Return manifests which needs to be created for given state."""
            logger.info(f"Got new request with parent: {parent} and children {children}")
            context = {"namespace": parent.get("metadata", {}).get("name")}
            pipeline_enabled = parent.get("metadata", {}).get("labels", {}).get(label)

            if pipeline_enabled != "true":
                logger.info(
                    f"Namespace not in scope, no action taken (metadata.labels.{label} = {pipeline_enabled}, must be 'true')"  # noqa: E501
                )
                return {"status": {}, "children": []}

            desired_secret_count = 1
            desired_resources = []
            desired_status = {
                "resources-ready": str(len(children["Secret.v1"]) == desired_secret_count)
            }

            desired_resources += generate_manifests(folder, context)
            return {"status": desired_status, "children": desired_resources}

        def do_POST(self):  # noqa: N802
            """Serve the sync() function as a JSON webhook."""
            observed = json.loads(self.rfile.read(int(self.headers.get("content-length"))))
            desired = self.sync(observed["parent"], observed["children"])

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(json.dumps(desired), "utf-8"))

    return HTTPServer((url, int(controller_port)), Controller)


def generate_manifests(templates_folder: str, context: dict) -> list[dict]:
    """For each file in templates_folder generate a yaml with populated context."""
    template_files = glob.glob(f"{templates_folder}/*.j2")
    logger.info(f"found files {template_files}")
    manifests = []
    for template_file in template_files:
        template = Template(Path(template_file).read_text())
        rendered_template = template.render(**context)
        tmp_yaml = yaml.safe_load(rendered_template)
        manifests.append(tmp_yaml)
    return manifests
