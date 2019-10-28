# -*- coding: utf-8 -*-

"""
General utility functions.
"""

from cachetools import cached, TTLCache

from settings import env

import asyncio


#@cached(cache=TTLCache(maxsize=25, ttl=env['UPTIME_CACHE_TTL']))
def asyncCachedTimedFileIO(fn: str) -> str:
    """
    Cache the default directory-type storage pool definition from disk.

    Args:
        fn: Name of the file to read.

    Returns:
        The base XML for defining a storage pool as a string.
    """
    with open(fn, 'r') as fh:
        return fh.read()