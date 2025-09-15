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
from bazooka import exceptions as bazooka_exc
from gcl_sdk.clients.http import base as http_client

from genesis_ci_tools import constants as c


def list_manifest(
    client: http_client.CollectionBaseClient, **filters
) -> list[dict[str, tp.Any]]:
    return client.filter(c.MANIFEST_COLLECTION, **filters)


def add_manifest(
    client: http_client.CollectionBaseClient,
    manifest: dict[str, tp.Any],
) -> dict[str, tp.Any]:
    uuid = sys_uuid.uuid4()
    if "uuid" in manifest:
        uuid = sys_uuid.UUID(manifest["uuid"])
    else:
        manifest["uuid"] = str(uuid)

    try:
        manifest_resp = client.create(c.MANIFEST_COLLECTION, data=manifest)
    except bazooka_exc.ConflictError:
        raise click.ClickException(f"Manifest with UUID {uuid} already exists")

    return manifest_resp


def delete_manifest(
    client: http_client.CollectionBaseClient,
    uuid: sys_uuid.UUID,
) -> None:
    try:
        client.delete(c.MANIFEST_COLLECTION, uuid=uuid)
    except bazooka_exc.NotFoundError:
        raise click.ClickException(f"Manifest with UUID {uuid} not found")


def install_manifest(
    client: http_client.CollectionBaseClient,
    uuid: sys_uuid.UUID,
) -> None:
    try:
        client.do_action(
            c.MANIFEST_COLLECTION, uuid=uuid, name="install", invoke=True
        )
    except bazooka_exc.ConflictError:
        raise click.ClickException(
            f"Manifest with UUID {uuid} already installed"
        )


def uninstall_manifest(
    client: http_client.CollectionBaseClient,
    uuid: sys_uuid.UUID,
) -> None:
    try:
        client.do_action(
            c.MANIFEST_COLLECTION, uuid=uuid, name="uninstall", invoke=True
        )
    except bazooka_exc.NotFoundError:
        raise click.ClickException(f"Manifest with UUID {uuid} not found")


def list_elements(
    client: http_client.CollectionBaseClient, **filters
) -> list[dict[str, tp.Any]]:
    return client.filter(c.ELEMENT_COLLECTION, **filters)
