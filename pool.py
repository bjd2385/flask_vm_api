#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple ZPool dataset manager for VMs.
"""

from typing import List, Optional
from asyncio.subprocess import PIPE, create_subprocess_shell

from settings import env

import re

# RE
newlines = re.compile(r'\n+')


class DatasetManager:
    """
    Provide a quick Python-native API for managing ZFS pool datasets for
    the VM API.
    """

    def __init__(self, machineImage: str, datasetName: str, host: Optional[str] =None) -> None:
        self.machineImage = machineImage
        self.datasetName = datasetName
        self.hostString = f'ssh {host} ' if host else ''

        if len(self.datasetName) > 1 and self.datasetName[-1] == '/':
            self.datasetName = self.datasetName[:-1]

    @staticmethod
    async def _getIO(command: str) -> List[str]:
        """
        Get results from terminal commands as lists of lines of text.
        """
        proc = await create_subprocess_shell(command, shell=True, stdout=PIPE, stderr=PIPE)
        stdout, stderr = await proc.communicate()

        if stderr:
            raise ValueError('Command exited with errors: {}'.format(stderr))

        if stdout:
            stdout = re.split(newlines, stdout.decode())

            # For some reason, `shell=True` likes to yield an empty string.
            if stdout[-1] == '':
                stdout = stdout[:-1]

        return stdout

    async def clone(self) -> Optional[str]:
        """
        Asynchronously clone a dataset by making a call to shell (possibly even to
        a remote host).

        Returns:
            Nothing if successful, a string with the error message otherwise.
        """
        try:
            await self._getIO(self.hostString + f'zfs clone {self.machineImage} {self.datasetName}')
        except ValueError as err:
            return f'Error {err}'

    async def inject(self, ip: str, hostname: str) -> Optional[str]:
        """
        Inject properties into the cloned disk image.

        Args:
            ip: IP address you wish the VM to have.
            hostname: Hostname you wish the VM to have.

        Returns:
            An optional string, if there was an error during injection.
        """
        loop = []
        try:
            mountPoint = await self.getMountPoint()

            # Loop up the `root.raw` disk image and inject our properties.
            loop = await self._getIO(self.hostString + f'losetup -fvP --show {mountPoint}/root.raw')
            await self._getIO(self.hostString + f'mount {loop[0]}p1 {env["REMOTE_LOOP_MOUNTPOINT"]}')

            # Now inject data into the disk image.
            await self._getIO(self.hostString + f'\'echo "    address {ip}" >> {env["REMOTE_LOOP_MOUNTPOINT"]}/etc/network/interfaces\'')
            await self._getIO(self.hostString + f'\'echo {hostname} > {env["REMOTE_LOOP_MOUNTPOINT"]}/etc/hostname\'')

        except ValueError as err:
            return f'Error {err}'
        finally:
            # We need to ensure that mount point is cleared and loop's taken down. The
            # only reason this may not happen is if it's a busy dataset / loop AFAIK.
            # E.g.:
            #     umount: / VMPool / test - DELETE: target is busy
            #     (In some cases useful info about processes that
            #     use the device is found by lsof(8) or fuser(1).)
            #     cannot unmount '/VMPool/test-DELETE': umount failed
            try:
                await self._getIO(self.hostString + f'umount {env["REMOTE_LOOP_MOUNTPOINT"]}')
                await self._getIO(self.hostString + f'losetup -d {loop[0]}')
            except ValueError:
                # We don't care if they didn't exist. Still work checking.
                pass

    async def getMountPoint(self) -> str:
        """
        Get the mount point of the dataset this instance encapsulates and cache it.

        Returns:
            String containing the path associated with the dataset.
        """
        try:
            mp = await self._getIO(self.hostString + f'zfs get mountpoint {self.datasetName} -Ho value')
            return mp[0]
        except ValueError as err:
            return f'Error {err}'


if __name__ == '__main__':
    from asyncio import run


    async def getResults() -> None:
        snap = 'VMPool/images/ubuntu_16@1567873253'
        dataset = 'VMPool/test-DELETE'
        dmh = DatasetManager(snap, dataset, host='root@perchost.bjd2385.com')
        call1 = await dmh.clone()
        call2 = await dmh.inject(ip='192.168.2.156', hostname='guest_vm')

        print(call1, call2)


    run(getResults())