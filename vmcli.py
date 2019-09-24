#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interact with my flask app for creating VMs, since I couldn't seem to get
terraform to work with my host.
"""

from mohawk.sender import Sender
from argparse import ArgumentParser


def cli() -> None:
    """
    Handle arguments and auth.
    """
    parser = ArgumentParser(description=__doc__)
    
    


if __name__ == '__main__':
    cli()
