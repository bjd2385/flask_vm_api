#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
A simple API for spinning up VM instances on my hosts.
"""

from typing import Any, List, Optional

from flask import Flask, redirect, request, jsonify
from secrets import token_hex
from mohawk.receiver import Receiver

from classes import LVConn

app = Flask(__name__)


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


@app.route('/list', methods=['POST'])
def lst() -> str:
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
    for host in hosts:
        with LVConn(f'qemu+ssh://{host}/system') as lv:
            VMs += lv.getDomains()
    return jsonify({'allVMs': VMs})


@app.route('/create', methods=['GET'])
def createVM() -> str:
    """
    Create the VM.
    """
    return "Me too!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
