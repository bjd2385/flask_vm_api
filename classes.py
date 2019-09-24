# -*- coding: utf-8 -*-

from typing import ContextManager, List, Any

import libvirt as lv


class LVConn(ContextManager['LVConn']):
    """
    RO-CM / wrapper for libvirt to make local system calls and extract 
    information about domains.
    """
    def __init__(self, system: str ='qemu:///system') -> None:
        # Other hosts may be referenced as
        # 'qemu+ssh://<hostname>/system <command>'
        self.system = system

    def __enter__(self) -> 'ROLibvirtConnection':
        """
        Set up the connection to libvirt; this will raise its own exception
        should the connection not be possible.
        """
        self.conn = lv.openReadOnly(self.system)
        return self

    def getDomains(self) -> List[str]:
        """
        Get all domains (equivalent to `virsh list --all`, in a way)
        """
        return list(map(lambda d: d.name(), self.conn.listAllDomains()))

    def getActiveDomains(self) -> List[str]:
        """
        Get a list of only active domains.
        """
        runningDomains = []

        # To get the state codes, see `virDomainState` enum defined in
        # https://libvirt.org/html/libvirt-libvirt-domain.html
        for dom in self.getDomains():
            if self.conn.lookupByName(dom).state()[0] == 1:
                runningDomains.append(dom)

        return runningDomains

    def getInactiveDomains(self) -> List[str]:
        """
        Opposite of `getActiveDomains`.
        """
        return list(set(self.getDomains()) - set(self.getActiveDomains()))

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()
