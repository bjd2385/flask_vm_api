# -*- coding: utf-8 -*-

"""
Provide a basic interface for interacting with a remote host on the back end of
the API.

TODO:
  1) Implement host resource checks prior to starting a VM.
  2) Extend the `terminate` method to take down the VM's directory-based storage pool.
"""

from typing import List, Any, Dict, Optional, Union
from operator import itemgetter

from pool import DatasetManager

import libvirt as lv


class LVConn:
    """
    CM / wrapper for libvirt to make local system calls and extract
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
        self.conn = lv.open(self.system)
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def getDomains(self) -> List[str]:
        """
        Get all domains (equivalent to `virsh list --all`, in a way)

        Returns:
            A list of all domains, regardless of state, indexed on this host.
        """
        return list(map(lambda d: d.name(), self.conn.listAllDomains()))

    def getActiveDomains(self) -> List[str]:
        """
        Produce a list of active (running) domains.

        Returns:
            A list of running domains.
        """
        runningDomains = []

        # To get the state codes, see `virDomainState` enum defined in
        # https://libvirt.org/html/libvirt-libvirt-domain.html
        for dom in self.getDomains():
            if self.conn.lookupByName(dom).state()[0] == 1:
                runningDomains.append(dom)

        return runningDomains

    def _getActiveDomainObjects(self) -> List[lv.virDomain]:
        """
        Produce domain objects instead of a list of names.

        It's a fortunate (?) coincidence that `listDomainsID` appears to
        only return IDs of VMs that are currently active on the node.
        
        Returns:
            A list of active libvirt virtual domain objects for further 
            interaction / method calls.
        """
        activeDomainIDs = self.conn.listDomainsID()
        activeDomainObjs = []
        for domainID in activeDomainIDs:
            activeDomainObjs.append(self.conn.lookupByID(domainID))
        return activeDomainObjs

    def getInactiveDomains(self) -> List[str]:
        """
        Opposite of `getActiveDomains`.
        
        Returns:
            A list of names of inactive (not running) domains.
        """
        return list(set(self.getDomains()) - set(self.getActiveDomains()))

    def getXML(self, domain: Union[str, int]) -> str:
        """
        Get the XML / template for a domain.

        Args:
            domain: The VM of interest.

        Returns:
            A string object containing the XML.
        """
        if type(domain) is str:
            return self.conn.lookupByName(domain).XMLDesc()
        else:
            return self.conn.lookupByID(domain).XMLDesc()

    def getActiveCores(self) -> int:
        """
        Get the number of assigned cores to VMs.
        """
        cpuCount = itemgetter(3)
        domObjs = self._getActiveDomainObjects()
        domObjsInfo = map(lambda obj: obj.info(), domObjs)
        return sum(map(cpuCount, domObjsInfo))

    def getRequestedMemory(self) -> int:
        """
        Return a sum of requested memory of active VMs (in kB) for a particular
        host.
        """
        kb = 0
        for domain in self._getActiveDomainObjects():
            kb += domain.maxMemory()
        return kb

    def getHostMemoryStats(self) -> Dict[str, Dict[str, int]]:
        """
        Return the memory status.
        """
        domains = dict()
        for domain in self._getActiveDomainObjects():
            memStats = domain.memoryStats()
            domains[domain.name()] = memStats
        return domains

    def getHypervisorType(self) -> str:
        """
        Get the name of the driver being used on the requested host.
        """
        return self.conn.getType()

    def getDomainStatus(self, domain: Union[str, int]) -> str:
        """
        Get the status of a libvirt domain.

        Args:
            domain: the respective VM / domain.

        Returns:
            The domain's status, as a string (e.g., 'running' or 'suspended')
        """
        if type(domain) is str:
            state = self.conn.lookupByName(domain).state()
        else:
            state = self.conn.lookupByID(domain).state()

        if state == lv.VIR_DOMAIN_RUNNING:
            return 'running'
        elif state == lv.VIR_DOMAIN_SHUTDOWN:
            return 'shutdown'
        elif state == lv.VIR_DOMAIN_SHUTOFF:
            return 'shut off'
        elif state == lv.VIR_DOMAIN_PAUSED:
            return 'paused'
        else:
            return f'unsupported domain state: {state}'

    def startVM(self, domain: Union[str, int]) -> str:
        """
        Start a VM on the connected host.

        Args:
            domain: the respective VM / domain.

        Returns:
            An empty string if the VM was started without an issue, and the error
            message otherwise, to be provided in an API's feedback.
        """
        if type(domain) is str:
            try:
                return self.conn.lookupByName(domain).create()
            except lv.libvirtError as err:
                return err.get_error_message()
        else:
            try:
                return self.conn.lookupByID(domain).create()
            except lv.libvirtError as err:
                return err.get_error_message()

    def shutdownVM(self, domain: Union[str, int]) -> str:
        """
        Request a shutdown of the respective domain. This is not guaranteed to
        produce results, however (hence the None return value).

        Args:
            domain: the respective VM / domain.
        """
        if type(domain) is str:
            try:
                return self.conn.lookupByName(domain).shutdown()
            except lv.libvirtError as err:
                return err.get_error_message()
        else:
            try:
                return self.conn.lookupByID(domain).shutdown()
            except lv.libvirtError as err:
                return err.get_error_message()

    def terminateVM(self, domain: Union[str, int]) -> str:
        """
        Destroy a domain, force shutdown.

        Args:
        Args:
            domain: the respective VM / domain.

        Returns:
            True if the VM was destroyed, False otherwise.
        """
        if type(domain) is str:
            try:
                return self.conn.lookupByName(domain).destroy()
            except lv.libvirtError as err:
                return err.get_error_message()
        else:
            try:
                return self.conn.lookupByID(domain).destroy()
            except lv.libvirtError as err:
                return err.get_error_message()

    def _createStoragePool(self) -> :

    @classmethod
    async def createVM(cls, host: str, guestName: str, ipAddress: str, dataset: str,
                 snapshot: str) -> Optional[str]:
        """
        Creates a VM on the requested host, given enough memory or processors are
        available. This is accomplished with the following steps:

        1) Clone the machine image (MI) by cloning a snapshot in ZFS and inject
           the IP address and hostname into the raw disk image `root.raw`.
        2) Add this MI's dataset as a storage pool to libvirt.
        3) Loop up the main disk image (which should be named `root.raw`), and
           inject the requested hostname and IP address into `/etc/hostname` and
           `/etc/network/interfaces`. This is the only currently-supported
           method.
        4) And, finally, generate a (basic) VM template. The VM is not started by
           default (but you can use the API to interact with this requested VM).

        Args:
            host: IP or FQDN by which libvirt can reach the host.
            ipAddress: IP address to be assigned to the guest VM.
            dataset: ZFS dataset to hold this VM's virtual disks.
            snapshot: ZFS snapshot (effectively a MI) to clone.

        Returns:
            A string object containing the XML template that was generated for
            this created VM.
        """
        dmh = DatasetManager(machineImage=snapshot, datasetName=dataset)
        error, = await dmh.clone(ipAddress, guestName, host)
        if error:
            return error

        with cls(system=f'qemu+ssh://{host}/system') as _lv:
            _lv._createStoragePool()


        return