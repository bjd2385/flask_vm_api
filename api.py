#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple API for spinning up VM instances on my hosts.
"""

from typing import Any, List, Optional

from flask import Flask, redirect, request, jsonify
from flask.wrappers import Response
from secrets import token_hex
from mohawk.receiver import Receiver

from classes import LVConn

app = Flask(__name__)


DEFAULT_HOST = 'b350-gaming-pc.bjd2385.com'


class Response:
    OK = 200
    Created = 201
    BadRequest = 400
    Unauthorized = 401
    NotFound = 404


class InvalidUsage(Exception):
    """
    Raised manually to give more context around API failures.
    """
    status_code = Response.BadRequest

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
    Return the main API webpage. For now, this reads index.html from file 
    on every request, but in the future it'll just be read into memory and 
    serve the page in that fashion.
    """
    with open('index.html', 'r') as indexh:
        index = indexh.read()
    return index


@app.route('/api/list', methods=['POST'])
def lst() -> Response:
    """
    List all available VMs across the listed hosts. Return a '400 error if
    a host does not exist.
    """
    data = request.get_json()
        
    if not data:
        raise InvalidUsage('Please provide a list of VMs.')

    if 'hosts' not in data:
        raise InvalidUsage('Must list hosts.')
    
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
    else:
        for host in hosts:
            with LVConn(f'qemu+ssh://{host}/system') as lv:
                VMs += lv.getDomains()
    return jsonify({'VMs': VMs})


@app.route('/api/resources', methods=['POST'])
def resources() -> Response:
    """
    Get the resources on a particular host that are being used by VMs.
    """
    data = request.get_json()

    if not data:
        data['hosts'] = DEFAULT_HOST

    # TODO:
    # - decide what kind of stats you want to return, including maybe
    #   - cores requested,
    #   - load average,
    #   - memory requested,
    #   - memory utilization
    
    response = {'stats': []}

    return jsonify(response)


@app.route('/api/xml', methods=['POST'])
def detail() -> Response:
    """
    Get VMs' XML template.
    """
    data = request.get_json()

    if 'guests' not in data:
        raise InvalidUsage(
            'Must provide a VM name or list of VMs from a host'
        )
    
    if 'host' in data:
        host = data['host']
    else:
        # Just default to my primary host.
        host = DEFAULT_HOST

    xml = dict()
    with LVConn(f'qemu+ssh://{host}/system') as lv:
        for vm in data['guests']:
            xml[vm] = lv.getXML(vm)
    
    return jsonify(xml)


@app.route('/api/create', methods=['POST'])
def create() -> str:
    """
    Create a VM and start it on a particular host.
    """
    return "Me too!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
