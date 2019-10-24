# -*- coding: utf-8 -*-

"""
Simple ZPool dataset manager for VMs.
"""

from weir import zfs

__all__ = [
    'DatasetManager'
]


class DatasetManager:
    """
    Provide a quick Python-native API for managing ZFS pool datasets.
    """
    def __init__(self, ) -> None:
        ...