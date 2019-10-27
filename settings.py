# -*- coding: utf-8 -*-

"""
Load environment variables.
"""

from dotenv import load_dotenv

import os
import socket

__all__ = ['env']

load_dotenv(verbose=True)

env = {
    'DEFAULT_HOST': socket.gethostname(),
    'VALID_HOSTS': os.getenv('VALID_HOSTS').split(';'),
    'API_BACKEND_USER': os.getenv('API_BACKEND_USER'),
    'UPTIME_CACHE_TTL': os.getenv('UPTIME_CACHE_TTL'),
    'UPTIME_CACHE': os.getenv('UPTIME_CACHE'),
    'REMOTE_LOOP_MOUNTPOINT': os.getenv('REMOTE_LOOP_MOUNTPOINT'),
    'REMOTE_LOOP_USER': os.getenv('REMOTE_LOOP_USER'),
    'DEFAULT_POOL_DEFINITION_PATH': os.getenv('DEFAULT_POOL_DEFINITION_PATH')
}

env['VALID_HOSTS_MAX'] = len(env['VALID_HOSTS'])

if env['DEFAULT_HOST'] not in env['VALID_HOSTS']:
    env['VALID_HOSTS'].append(env['DEFAULT_HOST'])