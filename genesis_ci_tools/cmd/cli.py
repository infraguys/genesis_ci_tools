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

import typing as tp
import uuid as sys_uuid

import click
import prettytable
from gcl_sdk.clients.http import base as http_client

from genesis_ci_tools import config as config_lib
from genesis_ci_tools import node as node_lib
from genesis_ci_tools import constants as c


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
            node["root_disk_size"],
            node["image"],
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
    "-e",
    "--endpoint",
    default="http://127.0.0.1:11010",
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
@click.pass_context
def main(
    ctx: click.Context,
    endpoint: str,
    user: str | None,
    password: str | None,
) -> None:
    # Prepare a client
    auth = http_client.CoreIamAuthenticator(
        base_url=endpoint, username=user, password=password
    )
    client = http_client.CollectionBaseClient(
        base_url=endpoint,
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
                node["root_disk_size"],
                node["image"],
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
