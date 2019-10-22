#! /usr/bin/env python3
# -*- coding: utf-8 -*-

from multiprocessing import cpu_count


bind = '0.0.0.0:5000'

# Maximum number of backlog requests to hold onto before users get error messages.
backlog = 100
workers = cpu_count() * 2 + 1

# Do not support persistent connections. Close after each request.
worker_class = 'sync'

# Kill a worker if it does not report to the master process.
timeout = 30

keepalive = 2

# Install a trace function that spews every line executed by the server.
spew = False

# Eventually, I'll want this to run as a daemon so it starts on boot.
daemon = False

# Environment variables to pass.
raw_env = []

pidfile = '/tmp/gunicorn_vm_api.pid'

umask = 755

user = 1000
group = 1000

tmp_upload_directory = None

# Log errors received to stdout with `-`
error_log = '-'
access_log = '-'
