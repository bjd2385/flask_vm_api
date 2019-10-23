# -*- coding: utf-8 -*-

from typing import List, Any, Dict
from operator import itemgetter

import libvirt as lv


class LVConn:
    """
    RO-CM / wrapper for libvirt to make local system calls and extract 
    information about domains.
    """
    def __init__(self, system: str ='qemu:///system') -> None:
        # Other hosts may be referenced as
        # 'qemu+ssh://<hostname>/system <command>'
        self.system = system

    def __enter__(self) -> 'LVConn':
        """
        Set up the connection to libvirt; this will raise its own exception
        should the connection not be possible.
        """
        self.conn = lv.openReadOnly(self.system)
        return self

    def __exit__(self, *args: Any) -> None:
        self.conn.close()

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

    def getActiveDomainObjects(self) -> List[lv.virDomain]:
        """
        Return the domain objects instead of a list of names.

        It's a fortunate (?) coincidence that `listDomainsID` appears to
        only return IDs of VMs that are currently active on the node.
        """
        activeDomainIDs = self.conn.listDomainsID()
        activeDomainObjs = []
        for domainID in activeDomainIDs:
            activeDomainObjs.append(self.conn.lookupByID(domainID))
        return activeDomainObjs

    def getInactiveDomains(self) -> List[str]:
        """
        Opposite of `getActiveDomains`.
        """
        return list(set(self.getDomains()) - set(self.getActiveDomains()))

    def getXML(self, domain: str) -> str:
        """
        Get the XML from domain.
        """
        return self.conn.lookupByName(domain).XMLDesc()

    def getActiveCores(self) -> int:
        """
        Get the number of assigned cores to VMs.
        """
        cpuCount = itemgetter(3)
        domObjs = self.getActiveDomainObjects()
        domObjsInfo = map(lambda obj: obj.info(), domObjs)
        return sum(map(cpuCount, domObjsInfo))

    def getRequestedMemory(self) -> int:
        """
        Return a sum of requested memory of active VMs (in kB) for a particular
        host.
        """
        kb = 0
        for domain in self.getActiveDomainObjects():
            kb += domain.maxMemory()
        return kb

    def getHostMemoryStats(self) -> Dict[str, Dict[str, int]]:
        """
        Return the memory status.
        """
        domains = dict()
        for domain in self.getActiveDomainObjects():
            memStats = domain.memoryStats()
            domains[domain.name()] = memStats
        return domains

    def getHypervisorType(self) -> str:
        """
        Get the name of the driver being used on this host.
        """
        return self.conn.getType()

    def close(self) -> None:
        self.conn.close()
