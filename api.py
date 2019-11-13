#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple API for spinning up VM instances on my hosts.
"""

from typing import Any, Optional, List, Dict
from flask import Flask, request, jsonify, abort, Response
from ast import literal_eval
from ipaddress import ip_address
from http import HTTPStatus
from cachetools import cached, TTLCache
from asyncio import run

from libvirtConnector import LVConn
from settings import env
from utils import asyncCachedTimedFileIO


app = Flask(__name__)


class InvalidUsage(Exception):
    """
    Raised manually to give more context around API failures.
    """
    status_code = HTTPStatus.BAD_REQUEST

    def __init__(self, message: str, status_code: Optional[int] =None,
                 payload: Optional[dict] =None) -> None:
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self) -> dict:
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


def checkValidHosts(*hosts: str) -> bool:
    """
    Verify requested hosts against acceptable hosts env variable.

    1) This checks to ensure that the number of requested hosts is not
    greater than the number of valid hosts, followed by
    2) a check to ensure each requested host is in the valid hosts env var.

    Args:
        Any number of hosts.

    Returns:
        `True` if it's a valid host, as compared against the env.
    """
    return len(hosts) <= env['VALID_HOSTS_MAX'] and all(host in env['VALID_HOSTS'] for host in hosts)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error: InvalidUsage) -> Any:
    """
    Error handler for invalid usage of this API.
    """
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/api/', methods=['GET'])
@app.route('/', methods=['GET'])
def index() -> str:
    """
    Return the main API web page (cached once accessed for an hour in the
    server's memory).
    """
    ind = asyncCachedTimedFileIO('static_html_pages/index.html')
    return ind


@app.route('/api/list', methods=['POST'])
def lst() -> Response:
    """
    List all available VMs across the listed hosts. Return a '400 error if
    a host does not exist.

    Request format:
        /api/list?hosts=<host 1>,<host 2>&status=[active|inactive]

    Returns:
        A JSON string of schema

        {
            "VMs": {
                "<active|inactive|all>": [
                    "VM_1",
                    ...
                ]
            }
        }

        containing a list of either active, inactive, or simply all VMs across the
        defined list of hosts in env.
    """
    data = request.get_json()

    if not data:
        raise InvalidUsage('Please provide a list of VMs.')

    if 'hosts' not in data or not data['hosts']:
        raise InvalidUsage('Must list hosts.')
    elif not checkValidHosts(*data['hosts']):
        raise InvalidUsage('Must provide valid hosts')

    hosts = data['hosts']
    VMs = []
    if 'status' in data:
        for host in hosts:
            with LVConn(f'qemu+ssh://{host}/system') as lv:
                if data['status'] == 'active':
                    VMs += lv.getActiveDomains()
                elif data['status'] == 'inactive':
                    VMs += lv.getInactiveDomains()
                else:
                    raise InvalidUsage(
                        'Must specify content \'active\' or \'inactive.\''
                    )
        return jsonify({'VMs': {data['status']: VMs}})
    else:
        for host in hosts:
            with LVConn(f'qemu+ssh://{host}/system') as lv:
                VMs += lv.getDomains()
        return jsonify({'VMs': {'all': VMs}})


@app.route('/api/xml', methods=['POST'])
def xml() -> Response:
    """
    Get VMs' XML template from one particular host.

    Request format:

        /api/xml?guests=<guest 1>,<guest 2>

    API Args:
        guests: List of guests to return the template for.
        host: The host upon which these guests reside.

    Returns:
        A JSON object of schema

        {
            <host>:
                "guestTemplates": [
                    {
                        <VM_1>: "template",
                    }
                    ...
                ]
        }
    """
    data = request.get_json()

    if 'guests' not in data:
        raise InvalidUsage(
            'Must provide a VM name or list of VMs from a host'
        )

    if 'host' in data:
        if checkValidHosts(data['host']):
            host = data['host']
        else:
            raise InvalidUsage('Must provide a single valid host.')
    else:
        # Just default to my primary host.
        host = env['DEFAULT_HOST']

    xml = dict()
    xml['guestTemplates'] = []
    with LVConn(f'qemu+ssh://{host}/system') as lv:
        for vm in data['guests']:
            xml['guestTemplates'].append({vm: lv.getXML(vm)})

    return jsonify({data['host']: xml})


@cached(cache=TTLCache(maxsize=1, ttl=env['UPTIME_CACHE_TTL']))
def uptimeCache() -> Dict[str, List[float]]:
    """
    Read the uptime on-disk cache and cache it in memory for quicker
    access.
    """
    with open(env['UPTIME_CACHE'], 'r') as fh:
        loadAvgs = literal_eval(fh.read().replace('\n', ''))

    for server in loadAvgs:
        loadAvgs[server] = loadAvgs[server].split(', ')

    # If this raises a 500 error to the end user, it's a sign the env
    # was not set up properly.
    if not all(server in env['VALID_HOSTS'] for server in loadAvgs):
        abort(HTTPStatus.INTERNAL_SERVER_ERROR)

    return loadAvgs


@app.route('/api/resources', methods=['POST'])
def resources() -> Response:
    """
    Get the resources available on a list of hosts.

    Default host specs are returned if no others are defined.

    API Args:
        (Optional) hosts: By default, whatever the environment variable is set to.

    Returns:
        A JSON object of the schema:

        TODO: Fill out schema once #6 above has been resolved.
    """
    data = request.get_json()
    if not data:
        data['hosts'] = env['DEFAULT_HOST']
    if not checkValidHosts(*data['hosts']):
        raise InvalidUsage('Must provide valid hosts.')

    hostResources = dict()
    for host in data['hosts']:
        hostState = {}

        with LVConn(f'qemu+ssh://{host}/system') as lv:
            hostState['activeCores'] = lv.getActiveCores()
            hostState['requestedMemory'] = lv.getRequestedMemory()
            hostState['memoryStats'] = lv.getHostMemoryStats()
        hostState['hostCPULoadAverages'] = uptimeCache()[host]
        
        hostResources[host] = hostState

    return jsonify({'hosts': hostResources})


@app.route('/api/create', methods=['POST'])
def create() -> Response:
    """
    Create a VM on a particular host.

    Request format:
    
        /api/create?host=<some host>&cpus=#&mem=<amount in GiB>&...

    API Args:
        host: Host upon which to create a VM.
        guestName: Guest VM's hostname to inject.
        ipAddress: The IP address to inject.
        datasetName: Dataset name to clone to.
        sourceSnapshot: MI from which to create the guest.

    Returns:
        A JSON object of the schema

        {
            "<host>": {
                "template": "<XML doc from the guest>"
            }
        }
    """
    data = request.get_json()
    print(data)
    # Validate all of our input fields.
    if 'host' in data:
        if checkValidHosts(data['host']):
            host = f'root@{data["host"]}'
        else:
            raise InvalidUsage('Must provide a single valid host.')
    else:
        # Just default to my primary host.
        host = f'root@{env["DEFAULT_HOST"]}'

    if 'guestName' in data and data['guestName']:
        guestName = data['guestName']
    else:
        raise InvalidUsage('Must provide a valid guest VM name.')

    if 'ipAddress' in data:
        try:
            ipAddress = str(ip_address(data['ipAddress']))
        except ValueError as err:
            abort(HTTPStatus.BAD_REQUEST)
            ipAddress = None
    else:
        raise InvalidUsage(
            'Must provide a valid IP address to assign the guest VM.'
        )

    if 'datasetName' in data and data['datasetName']:
        dataset = data['datasetName']
    else:
        raise InvalidUsage('Must provide a valid dataset name to contain VM.')

    if 'sourceSnapshot' in data and data['sourceSnapshot']:
        sourceSnapshot = data['sourceSnapshot']
    else:
        sourceSnapshot = env['DEFAULT_SNAPSHOT']

    if 'bridge' in data and data['bridge']:
        bridge = data['bridge']
    else:
        raise InvalidUsage('Must define bridge interface to use')

    if 'memory' in data and data['memory']:
        try:
            memory = int(data['memory'])
        except TypeError as err:
            abort(HTTPStatus.BAD_REQUEST)
            memory = None
    else:
        memory = 1024

    if 'cpus' in data and data['cpus']:
        try:
            cpus = int(data['cpus'])
        except TypeError as err:
            abort(HTTPStatus.BAD_REQUEST)
            cpus = None
    else:
        cpus = 1

    if 'template' in data and data['template']:
        template = data['template']
    else:
        template = 'ubuntu'

    # Now let's create the VM.
    with LVConn(f'qemu+ssh://{host}/system') as lv:
        template = run(lv.createVM(dataset, sourceSnapshot, guestName, ipAddress,
                                   bridge, memory, cpus, template))

    return jsonify({'VM': {'template': template}})


@app.route('/api/state', methods=['POST'])
def state() -> Response:
    """
    Make state calls to defined domains (e.g., similar to
    `virsh (start|destroy|undefine|stop)`.

    API Args:


    Returns:

    """