#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from __future__ import annotations

import os
import time
import typing as tp
import uuid as sys_uuid

import click
import prettytable
import yaml
from gcl_sdk.clients.http import base as http_client

from genesis_ci_tools import config as config_lib
from genesis_ci_tools import node as node_lib
from genesis_ci_tools import elements as elements_lib
from genesis_ci_tools import repo as repo_lib
from genesis_ci_tools import constants as c
from genesis_ci_tools import logger


class CmdContext(tp.NamedTuple):
    client: http_client.CollectionBaseClient


def _print_node(node: dict) -> None:
    table = prettytable.PrettyTable()
    table.field_names = [
        "UUID",
        "Project",
        "Name",
        "Cores",
        "RAM",
        "Root Disk",
        "Image",
        "IP",
        "Status",
    ]
    table.add_row(
        [
            node["uuid"],
            node["project_id"],
            node["name"],
            node["cores"],
            node["ram"],
            node["disk_spec"]["size"],
            node["disk_spec"]["image"],
            node["default_network"].get("ipv4", ""),
            node["status"],
        ]
    )
    click.echo(table)


def _print_config(config: dict) -> None:
    table = prettytable.PrettyTable()
    table.field_names = [
        "UUID",
        "Name",
        "Path",
        "Mode",
        "Owner",
        "Group",
        "Status",
    ]
    table.add_row(
        [
            config["uuid"],
            config["name"],
            config["path"],
            config["mode"],
            config["owner"],
            config["group"],
            config["status"],
        ]
    )
    click.echo(table)


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    default=os.path.expanduser("~/.genesis/genesisctl.yaml"),
    show_default=True,
    type=click.Path(exists=False, dir_okay=False),
    help="Path to YAML config file",
)
@click.option(
    "-e",
    "--endpoint",
    default="http://localhost:11010",
    show_default=True,
    help="Genesis API endpoint",
)
@click.option(
    "-u",
    "--user",
    default=None,
    help="Client user name",
)
@click.option(
    "-p",
    "--password",
    default=None,
    help="Password for the client user",
)
@click.option(
    "-P",
    "--project-id",
    default=None,
    type=click.UUID,
    help="Project ID for the client user",
)
@click.pass_context
def main(
    ctx: click.Context,
    config: str,
    endpoint: str,
    user: str | None,
    password: str | None,
    project_id: sys_uuid.UUID | None,
) -> None:
    # Load configuration from file (if exists)
    cfg_path = os.path.expanduser(config) if config else None
    cfg: dict = {}
    if cfg_path and os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
        except OSError as e:
            raise click.ClickException(
                f"Could not read config file '{cfg_path}': {e}"
            )
        except yaml.YAMLError as e:
            raise click.ClickException(
                f"Error parsing YAML file '{cfg_path}': {e}"
            )

        if not isinstance(loaded, dict):
            raise click.ClickException(
                "Config file must contain a YAML mapping"
            )
        cfg = loaded

    # Determine parameter sources to respect CLI priority over config
    ps = ctx.get_parameter_source

    def _get_final_value(param_name: str, cli_value: tp.Any) -> tp.Any:
        if ps(param_name) == click.core.ParameterSource.COMMANDLINE:
            return cli_value
        return cfg.get(param_name, cli_value)

    final_endpoint = _get_final_value("endpoint", endpoint)
    final_user = _get_final_value("user", user)
    final_password = _get_final_value("password", password)

    # Project ID
    final_project_id = None
    if ps("project_id") == click.core.ParameterSource.COMMANDLINE:
        final_project_id = project_id
    else:
        if cfg_project := cfg.get("project_id"):
            try:
                final_project_id = sys_uuid.UUID(str(cfg_project))
            except (ValueError, AttributeError) as exc:
                raise click.ClickException(
                    f"Invalid project_id in config: {cfg_project}"
                ) from exc

    # Prepare a client
    if final_project_id is not None:
        scope = http_client.CoreIamAuthenticator.project_scope(
            final_project_id
        )
    else:
        scope = None

    auth = http_client.CoreIamAuthenticator(
        base_url=final_endpoint,
        username=final_user,
        password=final_password,
        scope=scope,
    )
    client = http_client.CollectionBaseClient(
        base_url=final_endpoint,
        auth=auth,
    )
    ctx.obj = CmdContext(client)


@main.group("nodes", help="Manager nodes in the Genesis installation")
def nodes_group():
    pass


@nodes_group.command("list", help="List nodes")
@click.option(
    "-P",
    "--project-id",
    type=str,
    default=None,
    help="Filter nodes by project",
)
@click.pass_context
def list_node_cmd(
    ctx: click.Context,
    project_id: str | None,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    table = prettytable.PrettyTable()
    nodes = node_lib.list_nodes(client, project_id)

    table.field_names = [
        "UUID",
        "Project",
        "Name",
        "Cores",
        "RAM",
        "Root Disk",
        "Image",
        "IP",
        "Status",
    ]

    for node in nodes:
        table.add_row(
            [
                node["uuid"],
                node["project_id"],
                node["name"],
                node["cores"],
                node["ram"],
                node["disk_spec"]["size"],
                node["disk_spec"]["image"],
                node["default_network"].get("ipv4", ""),
                node["status"],
            ]
        )

    print(table)


@nodes_group.command("add", help="Add a new node to the Genesis installation")
@click.pass_context
@click.option(
    "-u",
    "--uuid",
    type=click.UUID,
    default=None,
    help="UUID of the node",
)
@click.option(
    "-p",
    "--project-id",
    type=click.UUID,
    required=True,
    help="Name of the project in which to deploy the node",
)
@click.option(
    "-c",
    "--cores",
    type=int,
    default=1,
    show_default=True,
    help="Number of cores to allocate for the node",
)
@click.option(
    "-r",
    "--ram",
    type=int,
    default=1024,
    show_default=True,
    help="Amount of RAM in Mb to allocate for the node",
)
@click.option(
    "-d",
    "--root-disk",
    type=int,
    default=10,
    show_default=True,
    help="Number of GiB of root disk to allocate for the node",
)
@click.option(
    "-i",
    "--image",
    type=str,
    required=True,
    help="Name of the image to deploy",
)
@click.option(
    "-n",
    "--name",
    type=str,
    default="node",
    help="Name of the node",
)
@click.option(
    "-D",
    "--description",
    type=str,
    default="",
    help="Description of the node",
)
@click.option(
    "--wait",
    type=bool,
    is_flag=True,
    default=False,
    help="Wait until the node is running",
)
def add_node_cmd(
    ctx: click.Context,
    uuid: sys_uuid.UUID | None,
    project_id: sys_uuid.UUID,
    cores: int,
    ram: int,
    root_disk: int,
    image: str,
    name: str,
    description: str,
    wait: bool,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    node = node_lib.add_node(
        client,
        uuid,
        project_id,
        cores,
        ram,
        root_disk,
        image,
        name,
        description,
        wait,
    )
    _print_node(node)


@nodes_group.command(
    "add-or-update", help="Add a new node or update an existing one"
)
@click.pass_context
@click.option(
    "-u",
    "--uuid",
    type=click.UUID,
    default=None,
    help="UUID of the node",
)
@click.option(
    "-p",
    "--project-id",
    type=click.UUID,
    required=True,
    help="Name of the project in which to deploy the node",
)
@click.option(
    "-c",
    "--cores",
    type=int,
    default=1,
    show_default=True,
    help="Number of cores to allocate for the node",
)
@click.option(
    "-r",
    "--ram",
    type=int,
    default=1024,
    show_default=True,
    help="Amount of RAM in Mb to allocate for the node",
)
@click.option(
    "-d",
    "--root-disk",
    type=int,
    default=10,
    show_default=True,
    help="Number of GiB of root disk to allocate for the node",
)
@click.option(
    "-i",
    "--image",
    type=str,
    required=True,
    help="Name of the image to deploy",
)
@click.option(
    "-n",
    "--name",
    type=str,
    default="node",
    help="Name of the node",
)
@click.option(
    "-D",
    "--description",
    type=str,
    default="",
    help="Description of the node",
)
@click.option(
    "--wait",
    type=bool,
    is_flag=True,
    default=False,
    help="Wait until the node is running",
)
def add_or_update_node_cmd(
    ctx: click.Context,
    uuid: sys_uuid.UUID | None,
    project_id: sys_uuid.UUID,
    cores: int,
    ram: int,
    root_disk: int,
    image: str,
    name: str,
    description: str,
    wait: bool,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    node = node_lib.add_or_update_node(
        client,
        uuid,
        project_id,
        cores,
        ram,
        root_disk,
        image,
        name,
        description,
        wait,
    )
    _print_node(node)


@nodes_group.command("delete", help="Delete node")
@click.argument(
    "uuid",
    type=click.UUID,
)
@click.pass_context
def delete_node_cmd(
    ctx: click.Context,
    uuid: sys_uuid.UUID | None,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    node_lib.delete_node(client, uuid)


@main.group("configs", help="Manager configs in the Genesis installation")
def configs_group():
    pass


@configs_group.command("list", help="List configs")
@click.option(
    "-n",
    "--node",
    type=click.UUID,
    default=None,
    help="Filter configs by node",
)
@click.pass_context
def list_config_cmd(
    ctx: click.Context,
    node: sys_uuid.UUID | None,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    table = prettytable.PrettyTable()

    configs = config_lib.list_config(client, node)

    table.field_names = [
        "UUID",
        "Name",
        "Path",
        "Mode",
        "Owner",
        "Group",
        "Status",
    ]

    for config in configs:
        table.add_row(
            [
                config["uuid"],
                config["name"],
                config["path"],
                config["mode"],
                config["owner"],
                config["group"],
                config["status"],
            ]
        )

    print(table)


@configs_group.command(
    "add-from-env", help="Add configuration from environment variables"
)
@click.option(
    "-p",
    "--project-id",
    type=click.UUID,
    required=True,
    help="Project ID ofthe config",
)
@click.option(
    "--env-prefix",
    default="GCT_ENV_",
    help="Prefix used to filter environment variables for envs",
)
@click.option(
    "--env-path",
    default="/var/lib/genesis/app.env",
    help="Path to the env file will be saved on the node",
)
@click.option(
    "--env-format",
    default="env",
    type=click.Choice([s for s in tp.get_args(c.ENV_FILE_FORMAT)]),
    show_default=True,
    help="Format of the env file",
)
@click.option(
    "--cfg-prefix",
    default="GCT_CFG_",
    help="Prefix used to filter environment variables for configs",
)
@click.option(
    "--base64",
    is_flag=True,
    default=False,
    help="Base64 encode is enabled for configs",
)
@click.argument("node", type=click.UUID)
@click.pass_context
def add_config_from_env_cmd(
    ctx: click.Context,
    project_id: sys_uuid.UUID,
    env_prefix: str,
    env_path: str,
    env_format: c.ENV_FILE_FORMAT,
    cfg_prefix: str,
    base64: bool,
    node: sys_uuid.UUID,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    config_lib.add_config_from_env(
        client,
        project_id,
        env_prefix,
        env_path,
        env_format,
        cfg_prefix,
        base64,
        node,
    )


@configs_group.command(
    "delete", help="Delete configuration from environment variables"
)
@click.option(
    "-u",
    "--uuid",
    type=click.UUID,
    default=None,
    help="Config UUID",
)
@click.option(
    "-n",
    "--node",
    type=click.UUID,
    default=None,
    help="Delete all configs for the node",
)
@click.pass_context
def delete_config_cmd(
    ctx: click.Context,
    uuid: sys_uuid.UUID | None,
    node: sys_uuid.UUID | None,
) -> None:
    client: http_client.CollectionBaseClient = ctx.obj.client
    config_lib.delete_config(client, uuid, node)


# Elements group
@main.group("elements", help="Manage elements in the Genesis installation")
def elements_group():
    pass


def apply_element(
    client: http_client.CollectionBaseClient,
    repository: str,
    path_or_name: str,
    install_only: bool = False,
) -> dict[str, tp.Any]:
    """Install or update element from a YAML file or repository.

    The command will install the element if it's not installed or update it
    if it's installed.
    """
    log = logger.ClickLogger()

    if os.path.exists(path_or_name):
        with open(path_or_name, "r", encoding="utf-8") as f:
            manifest = yaml.safe_load(f)
    else:
        manifest = repo_lib.download_manifest(repository, path_or_name)

    requirements: dict = manifest.get("requirements", {})

    installed = bool(elements_lib.list_elements(client, name=manifest["name"]))

    if installed and install_only:
        raise click.ClickException(
            f"Element {manifest['name']} is already installed"
        )

    apply_func = (
        elements_lib.install_manifest
        if install_only
        else elements_lib.apply_manifest
    )

    # Install element if no requirements
    if not requirements:
        manifest = elements_lib.add_manifest(client, manifest)
        apply_func(client, manifest["uuid"])
        return manifest

    # Resolve dependencies
    installed_elements = {
        e["name"] for e in elements_lib.list_elements(client)
    }
    required_elements = set(requirements.keys()) - installed_elements

    log.info(
        "The following elements will be installed: "
        f"{required_elements.union({manifest['name']})}"
    )

    while required_elements:
        # TODO(akremenetsky): Use queue to resolve dependencies
        requirement = required_elements.pop()
        req_manifest = repo_lib.download_manifest(repository, requirement)

        # Determine requirements for the element
        requirements = set(req_manifest.get("requirements", {}).keys())
        requirements = requirements - installed_elements
        required_elements.update(requirements)

        # NOTE(akremenetsky): We should install the element since there are
        # unresolved dependencies but for the simplicity we will install it here
        req_manifest = elements_lib.add_manifest(client, req_manifest)
        elements_lib.install_manifest(client, req_manifest["uuid"])
        log.important(f"Element {req_manifest['name']} installed successfully")

        installed_elements.add(req_manifest["name"])

        # TODO(akremenetsky): The installation is stuck for some reason
        # so we need to wait a bit. Solve the issue in GC and remove this
        # sleep.
        time.sleep(3)

    manifest = elements_lib.add_manifest(client, manifest)
    apply_func(client, manifest["uuid"])
    return manifest


@elements_group.command(
    "install", help="Install element from a manifest (YAML file)"
)
@click.option(
    "-r",
    "--repository",
    default="http://10.20.0.1:8080/genesis-elements/",
    show_default=True,
    help="Repository endpoint",
)
@click.argument("path_or_name")
@click.pass_context
def install_element_cmd(
    ctx: click.Context, repository: str, path_or_name: str
) -> None:
    """Install element from a YAML file"""
    log = logger.ClickLogger()
    manifest = apply_element(
        ctx.obj.client, repository, path_or_name, install_only=True
    )
    log.important(f"Element {manifest['name']} installed successfully")


@elements_group.command("update", help="Update element from a YAML file")
@click.option(
    "-r",
    "--repository",
    default="http://10.20.0.1:8080/genesis-elements/",
    show_default=True,
    help="Repository endpoint",
)
@click.argument("path_or_name")
@click.pass_context
def update_element_cmd(
    ctx: click.Context, repository: str, path_or_name: str
) -> None:
    """Update element from a YAML file"""
    log = logger.ClickLogger()
    manifest = apply_element(ctx.obj.client, repository, path_or_name)
    log.important(f"Element {manifest['name']} updated successfully")


@elements_group.command(
    "uninstall", help="Uninstall element by UUID, path or name"
)
@click.argument("path_uuid_name", type=str)
@click.pass_context
def uninstall_element_cmd(ctx: click.Context, path_uuid_name: str) -> None:
    """Uninstall element by UUID, path or name"""
    client: http_client.CollectionBaseClient = ctx.obj.client
    log = logger.ClickLogger()

    def _uninstall(uuid: sys_uuid.UUID) -> None:
        elements_lib.uninstall_manifest(client, uuid)
        elements_lib.delete_manifest(client, uuid)
        log.important(f"Element {uuid} uninstalled successfully")

    # UUID
    try:
        uuid = sys_uuid.UUID(path_uuid_name)
        _uninstall(uuid)
        return
    except ValueError:
        pass

    # Name
    name = path_uuid_name
    manifests = elements_lib.list_manifest(client, name=name)
    if len(manifests) == 1:
        uuid = manifests[0]["uuid"]
        _uninstall(uuid)
        return
    if len(manifests) > 1:
        raise click.ClickException(f"Multiple elements found with name {name}")

    # Path
    if os.path.exists(path_uuid_name):
        with open(path_uuid_name, "r") as f:
            manifest = yaml.safe_load(f)
        if "uuid" in manifest:
            filters = {"uuid": manifest["uuid"]}
        elif "name" in manifest:
            filters = {"name": manifest["name"]}
        else:
            raise click.ClickException("Manifest must have uuid or name")

        manifests = elements_lib.list_manifest(client, **filters)
        if len(manifests) == 1:
            uuid = manifests[0]["uuid"]
            _uninstall(uuid)
            return
        if len(manifests) > 1:
            raise click.ClickException(
                f"Multiple elements found with name {name}"
            )
        log.warn(f"Element {list(filters.values())[0]} not found")
        return

    log.warn(f"Element {path_uuid_name} not found")


@elements_group.command("list", help="List elements")
@click.pass_context
def list_element_cmd(ctx: click.Context) -> None:
    """List elements"""
    client: http_client.CollectionBaseClient = ctx.obj.client
    table = prettytable.PrettyTable()
    table.field_names = [
        "UUID",
        "Name",
        "Description",
        "Version",
        "Status",
    ]

    elements = elements_lib.list_elements(client)
    for element in elements:
        table.add_row(
            [
                element["uuid"],
                element["name"],
                element["description"],
                element["version"],
                element["status"],
            ]
        )
    click.echo(table)


@elements_group.command("show", help="Show element general information")
@click.argument("name")
@click.pass_context
def show_element_cmd(ctx: click.Context, name: str) -> None:
    """Show element general information"""
    client: http_client.CollectionBaseClient = ctx.obj.client
    log = logger.ClickLogger()

    element = elements_lib.list_elements(client, name=name)
    if not element:
        raise click.ClickException(f"Element {name} not found")

    if len(element) > 1:
        raise click.ClickException(f"Multiple elements found with name {name}")

    element = element[0]

    table = prettytable.PrettyTable()
    table.field_names = [
        "UUID",
        "Name",
        "Description",
        "Version",
        "Status",
    ]

    table.add_row(
        [
            element["uuid"],
            element["name"],
            element["description"],
            element["version"],
            element["status"],
        ]
    )

    click.echo(f"Element {name}:")
    click.echo(table)

    resources = elements_lib.list_resources(
        client, sys_uuid.UUID(element["uuid"])
    )
    table = prettytable.PrettyTable()
    table.field_names = [
        "UUID",
        "Name",
        "Kind",
        "Full hash",
        "Status",
        "Created at",
        "Updated at",
    ]

    for resource in resources:
        table.add_row(
            [
                resource["uuid"],
                resource["name"],
                resource["kind"],
                resource["full_hash"],
                resource["status"],
                resource["created_at"],
                resource["updated_at"],
            ]
        )

    click.echo("Resources:")
    click.echo(table)
