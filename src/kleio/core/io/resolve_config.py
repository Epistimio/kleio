# -*- coding: utf-8 -*-
"""
:mod:`kleio.core.resolve_config` -- Configuration parsing and resolving
=======================================================================

.. module:: resolve_config
   :platform: Unix
   :synopsis: How does kleio resolve configuration settings?

How:

 - Experiment name resolves like this:
    * cmd-arg **>** cmd-provided kleio_config **>** REQUIRED (no default is given)

 - Database options resolve with the following precedence (high to low):
    * cmd-provided kleio_config **>** env vars **>** default files **>** defaults

.. seealso:: :const:`ENV_VARS`, :const:`ENV_VARS_DB`


 - All other managerial, `Optimization` or `Dynamic` options resolve like this:

    * cmd-args **>** cmd-provided kleio_config **>** database (if experiment name
      can be found) **>** default files

Default files are given as a list at :const:`DEF_CONFIG_FILES_PATHS` and a
precedence is respected when building the settings dictionary:

 * default kleio example file **<** system-wide config **<** user-wide config

.. note:: `Optimization` entries are required, `Dynamic` entry is optional.

"""
import bson
import getpass
import logging
import os
import platform
import socket
import subprocess
import xml.etree.ElementTree

from numpy import inf as infinity
import yaml

import kleio
from kleio.core.utils import sorteddict
from kleio.core.io.cmdline_parser import CmdlineParser


def is_exe(path):
    """Test whether `path` describes an executable file."""
    return os.path.isfile(path) and os.access(path, os.X_OK)


log = logging.getLogger(__name__)

################################################################################
#                 Default Settings and Environmental Variables                 #
################################################################################

DEF_CONFIG_FILES_PATHS = [
    os.path.join(kleio.core.DIRS.site_data_dir, 'kleio_config.yaml.example'),
    os.path.join(kleio.core.DIRS.site_config_dir, 'kleio_config.yaml'),
    os.path.join(kleio.core.DIRS.user_config_dir, 'kleio_config.yaml')
    ]

# list containing tuples of
# (environmental variable names, configuration keys, default values)
ENV_VARS_DB = dict(
    name=('KLEIO_DB_NAME', 'kleio'),
    type=('KLEIO_DB_TYPE', 'MongoDB'),
    host=('KLEIO_DB_ADDRESS', socket.gethostbyname(socket.gethostname()))
    )

# TODO: Default resource from environmental (localhost)

# dictionary describing lists of environmental tuples (e.g. `ENV_VARS_DB`)
# by a 'key' to be used in the experiment's configuration dict
ENV_VARS = dict(
    database=ENV_VARS_DB,
    debug=('KLEIO_DEBUG_MODE', False)
    )


def fetch_config(args):
    """Return the config inside the .yaml file if present."""
    kleio_file = args.get('config')
    config = dict()
    if kleio_file:
        log.debug("Found kleio configuration file at: %s", os.path.abspath(kleio_file.name))
        kleio_file.seek(0)
        config = yaml.safe_load(kleio_file)

    return config


def fetch_default_options():
    """Create a dict with options from the default configuration files.

    Respect precedence from application's default, to system's and
    user's.

    .. seealso:: :const:`DEF_CONFIG_FILES_PATHS`

    """
    default_config = dict()

    # get default options for some managerial variables (see :const:`ENV_VARS`)
    default_config = fetch_env_vars(fetch_default=True)

    # fetch options from default configuration files
    for configpath in DEF_CONFIG_FILES_PATHS:
        try:
            with open(configpath) as f:
                cfg = yaml.safe_load(f)
                if cfg is None:
                    continue
                # implies that yaml must be in dict form
                for k, v in cfg.items():
                    if k in ENV_VARS:
                        default_config[k] = {}
                        for vk, vv in v.items():
                            default_config[k][vk] = vv
                    else:
                        if k != 'name':
                            default_config[k] = v
        except IOError as e:  # default file could not be found
            log.debug(e)
        except AttributeError as e:
            log.warning("Problem parsing file: %s", configpath)
            log.warning(e)

    return default_config


def fetch_env_vars(env_vars=None, fetch_default=False):
    """Fetch environmental variables related to kleio's managerial data."""
    if env_vars is None:
        env_vars = ENV_VARS

    config = {}

    for signif, evars in env_vars.items():

        if isinstance(evars, dict):
            config[signif] = fetch_env_vars(evars, fetch_default)
        elif os.getenv(evars[0]) is not None:
            config[signif] = os.getenv(evars[0])
        elif fetch_default:
            config[signif] = evars[1]

    return config


def fetch_metadata(cmdargs):
    """Infer rest information about the process + versioning"""
    metadata = {}

    # Move 'user_args' to 'metadata' key
    metadata['commandline'] = fetch_cmdline(cmdargs)

    # metadata['user'] = getpass.getuser()

    metadata['host'] = fetch_host_info(cmdargs)
    metadata['version'] = infer_versioning_metadata(cmdargs)

    return metadata


def fetch_cmdline(cmdargs):
    if 'commandline' not in cmdargs:
        return None

    cmdline_parser = CmdlineParser()
    configuration = cmdline_parser.parse(cmdargs['commandline'])
    return cmdline_parser.format(configuration).split(" ")


def merge_configs(*configs):
    """Merge configuration dictionnaries following the given hierarchy

    Suppose function is called as merge_configs(A, B, C). Then any pair (key, value) in C would
    overwrite any previous value from A or B. Same apply for B over A.

    If for some pair (key, value), the value is a dictionary, then it will either overwrite previous
    value if it was not also a directory, or it will be merged following
    `merge_configs(old_value, new_value)`.

    .. warning:

        Redefinition of subdictionaries may lead to confusing results because merges do not remove
        data.

        If for instance, we have {'a': {'b': 1, 'c': 2}} and we would like to update `'a'` such that
        it only have `{'c': 3}`, it won't work with {'a': {'c': 3}}.

        merge_configs({'a': {'b': 1, 'c': 2}}, {'a': {'c': 3}}) -> {'a': {'b': 1, 'c': 3}}

    Example
    -------
    .. code-block:: python
        :linenos:

        a = {'a': 1, 'b': {'c': 2}}
        b = {'b': {'c': 3}}
        c = {'b': {'c': {'d': 4}}}

        m = resolve_config.merge_configs(a, b, c)

        assert m == {'a': 1, 'b': {'c': {'d': 4}}}

        a = {'a': 1, 'b': {'c': 2, 'd': 3}}
        b = {'b': {'c': 4}}
        c = {'b': {'c': {'e': 5}}}

        m = resolve_config.merge_configs(a, b, c)

        assert m == {'a': 1, 'b': {'c': {'e': 5}, 'd': 3}}

    """
    merged_config = configs[0]

    for config in configs[1:]:
        for key, value in config.items():
            if isinstance(value, dict) and isinstance(merged_config.get(key), dict):
                merged_config[key] = merge_configs(merged_config[key], value)
            elif value is not None:
                merged_config[key] = value

    return merged_config


def infer_versioning_metadata(existing_metadata):
    """Infer information about user's script versioning if available."""
    # VCS system
    # User repo's version
    # User repo's HEAD commit hash
    return {}


def fetch_host_info(config):
    host_info = sorteddict()
    host_info['CPUs'] = fetch_cpus_info()
    host_info['GPUs'] = fetch_gpus_info()
    host_info['platform'] = fetch_platform_info()
    host_info['env_vars'] = fetch_host_env_vars(config)
    host_info['user'] = getpass.getuser()

    return host_info


def fetch_cpus_info():
    cpus_info = sorteddict()
    lscpu_output = subprocess.check_output("lscpu", shell=True).strip().decode()

    for line in lscpu_output.split("\n"):
        items = line.split(":")
        cpus_info[items[0]] = ":".join(item.strip(' \t') for item in items[1:])

    cpus_info.pop('CPU MHz', None)

    return cpus_info


def fetch_platform_info():

    platform_info = sorteddict()
    platform_info['kleio_version'] = kleio.core.__version__

    for key in list(sorted(platform.__dict__.keys())):
        if key.startswith('_'):
            continue

        item = getattr(platform, key)

        if callable(item):
            try:
                item = item()
            except BaseException as e:
                log.debug("Cannot call platform.{}: {}".format(key, str(e)))

        if not callable(item):
            try:
                bson.BSON.encode(dict(a=item))
            except bson.errors.InvalidDocument as e:
                if "Cannot encode" not in str(e):
                    raise
            else:
                platform_info[key] = item

    return platform_info 


def fetch_host_env_vars(config):
    host_env_vars = sorteddict()
    for env_var in config.get('host_env_vars', ['CLUSTER']):
        host_env_vars[env_var] = os.environ.get(env_var, None)

    return host_env_vars


def fetch_gpus_info():
    gpus_info = sorteddict()

    try:
        nvidia_xml = subprocess.check_output(['nvidia-smi', '-q', '-x']).decode()
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return {}

    for child in xml.etree.ElementTree.fromstring(nvidia_xml):
        if child.tag == 'driver_version':
            gpus_info['driver_version'] = child.text
        if child.tag != 'gpu':
            continue
        gpu = sorteddict((
            ('model', child.find('product_name').text),
            ('total_memory', (child.find('fb_memory_usage').find('total').text)),
            ('persistence_mode', (child.find('persistence_mode').text == 'Enabled'))
        ))
        gpus_info[child.attrib['id'].replace(".", ",")] = gpu

    return gpus_info
