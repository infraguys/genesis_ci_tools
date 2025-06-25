# Genesis CI Tools

Helpful tools for Continuous Integration (CI) of Genesis projects. The tools are based on CLI utilities that simplify interacting with the Genesis installation.
The main command is `genesis-ci`. It allows to create nodes, configs and other entities in the Genesis installations. For example, the `genesis-ci nodes list` command will list all nodes in the Genesis installation. `genesis-ci --help` will show all available commands.


# 📦 Installation

Install required packages:

Ubuntu:
```bash
sudo apt-get install libev-dev
```

Fedora:
```bash
sudo dnf install libev-devel
```

Initialize virtual environment with the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

# 🚀 Usage

After installation the `genesis-ci` command will be available in the terminal. For example, `genesis-ci nodes list` will list all nodes in the Genesis installation. Below you can find most useful commands:

Create nodes with specified parameters:
```bash
genesis-ci -e http://127.0.0.1:11010 -u test -p test nodes add \
    --project-id 00000000-0000-0000-0000-000000000000 \
    --image "http://10.20.0.1:8080/genesis-base.raw" \
    --cores 4 \
    --ram 8192 \
    --root-disk 20 \
    --name "my-node"
```

List nodes:
```bash
genesis-ci -e http://127.0.0.1:11010 -u test -p test nodes list
```

List configs:
```bash
genesis-ci -e http://127.0.0.1:11010 -u test -p test configs list
```

Delete node:
```bash
genesis-ci -e http://127.0.0.1:11010 -u test -p test nodes delete 00000000-0000-0000-0000-000000000001
```

## Configs from environment variables

One of the useful feature that need more explanation is the ability to create configs for nodes from environment variables. For this purpose we have `genesis-ci configs add-from-env` command. There are two formats of configurations that can be used to delivered to the node:

- As environment variables
- As plain text

In the `environment variable` all values should be placed in single file by path `--env-path`. To detect such variables the `--env-prefix` prefix will be used. The default value for this variable is `GCT_ENV_`. For example, if we have the variable `GCT_ENV_FOO=bar` it will be add to the config as `FOO=bar` on the node.

```bash
export GCT_ENV_FOO=bar

genesis-ci -e http://127.0.0.1:11010 -u test -p test configs add-from-env \
    --project-id <project-uuid> \
    <node-uuid>

# ... On the node ...

cat /var/lib/genesis/app.env

FOO=bar

```

Where `/var/lib/genesis/app.env` is default path.
There are two supported formats for the env file: `env` and `json`, use option `--env-format` to set the format.

In the `plain text` we need to specify at least two variables for path and content.

```bash
export GCT_CFG_TEXT_FOO='My content!'
export GCT_CFG_PATH_FOO=/home/my-user/config.txt

genesis-ci -e http://127.0.0.1:11010 -u test -p test configs add-from-env \
    --project-id <project-uuid> \
    <node-uuid>

# ... On the node ...

cat /home/my-user/config.txt

My content!

```

`--cfg-prefix` set the prefix for config variables. The default value is `GCT_CFG_`. Also the content can be decoded from base64. Use `--base64` flag to enable it.


# 💡 Contributing

Contributing to the project is highly appreciated! However, some rules should be followed for successful inclusion of new changes in the project:
- All changes should be done in a separate branch.
- Changes should include not only new functionality or bug fixes, but also tests for the new code.
- After the changes are completed and **tested**, a Pull Request should be created with a clear description of the new functionality. And add one of the project maintainers as a reviewer.
- Changes can be merged only after receiving an approve from one of the project maintainers.