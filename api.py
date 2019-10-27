#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple API for spinning up VM instances on my hosts.

TODO:
    1) Implement field schema parser to ensure additional fields can't be
       added to a request.
    2) Cache all host-level calls.
    3) Add a restricted user for host-level calls / information gathering. Problem
       is, I don't know how to implement this; thoughts are, maybe a restricted user
       that only has the ability to execute specific commands (e.g., `uptime`).
    4) `uptimeCache`, by default, reads the entire file into memory. It may be
       better to scale the number of cached results by the length of valid
       hosts (you never know how many you may have), then read a new file for
       each from disk as it's requested into memory.
    5) Add schema validation on input (and output?) JSON.
    6) Fix `resources` endpoint return structure. My goal at this time is just to
       get the data, which I've accomplished. Later, I need to come back and
       restructure it so it actually makes _sense_.
    7) At points of file IO, perhaps it would make sense on cache refresh to 
       add async IO and an async cache decorator.
    8) Spin off a worker to go create the ZFS dataset and VM from this API's threads.
       In other words, the API POST request would update a database and create a
       thread, which
    9) Refactor so that Libvirt connections are opened to all available hosts from
       the start, as opposed to opening them and tearing them down for every request.
"""

from typing import Any, Optional, List, Dict
from flask import Flask, request, jsonify, abort, Response
from cachetools import cached, TTLCache
from ast import literal_eval
from ipaddress import ip_address
from http import HTTPStatus

from libvirtConnector import LVConn
from settings import env


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


def checkValidHosts(*hosts: List[str]) -> bool:
    """
    Verify requested hosts against acceptable hosts env variable.

    1) This checks to ensure that the number of requested hosts is not
    greater than the number of valid hosts, followed by
    2) a check to ensure each requested host is in the valid hosts env var.

    Returns `True` if it's a valid host, as compared against the env.
    """
    return len(hosts) <= env['VALID_HOSTS_MAX'] and \
           all(host in env['VALID_HOSTS'] for host in hosts)


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
@cached(cache=TTLCache(maxsize=1, ttl=env['UPTIME_CACHE_TTL']))
def index() -> str:
    """
    Return the main API web page (cached once accessed for an hour in the
    server's memory).
    """
    with open('index.html', 'r') as indexh:
        ind = indexh.read()
    return ind


@app.route('/api/list', methods=['POST'])
def lst() -> Response:
    """
    List all available VMs across the listed hosts. Return a '400 error if
    a host does not exist.

    Request format:
        /api/list?hosts=<host 1>,<host 2>&status=[active|inactive]
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

        }
    """
    data = request.get_json()

    if 'guests' not in data:
        raise InvalidUsage(
            'Must provide a VM name or list of VMs from a host'
        )

    if 'host' in data:
        if len(data['host']) == 1 and checkValidHosts(data['host']):
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

    return jsonify(xml)


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

    @cached(cache=TTLCache(maxsize=1, ttl=300))
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


@app.route('/api/create', methods=['POST', 'GET'])
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
            "VM": "<XML doc from the guest>"
        }
    """
    data = request.get_json()

    # Validate all of our input fields.
    if 'host' in data:
        if len(data['host']) == 1 and checkValidHosts(data['host']):
            host = data['host']
        else:
            raise InvalidUsage('Must provide a single valid host.')
    else:
        # Just default to my primary host.
        host = env['DEFAULT_HOST']

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
        dataset = data['dataset_name']
    else:
        raise InvalidUsage('Must provide a valid dataset name to contain VM.')

    if 'sourceSnapshot' in data and data['sourceSnapshot']:
        sourceSnapshot = data['source_snapshot']
    else:
        sourceSnapshot = env['DEFAULT_SNAPSHOT']

    # Now let's create the VM.
    with LVConn(f'qemu+ssh://{host}/system') as lv:
        template = lv.createVM(host, guestName, ipAddress, dataset, sourceSnapshot)

    return jsonify({'VM': template})
