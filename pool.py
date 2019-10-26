#! /usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple ZPool dataset manager for VMs.
"""

from typing import List, Union, Optional
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

    def __init__(self, machineImage: str, datasetName: str) -> None:
        self.machineImage = machineImage
        self.datasetName = datasetName

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

    async def clone(self, ip: str, hostname: str, host: Optional[str] = None) -> Union[List[str], str]:
        """
        Asynchronously clone a dataset by making a call to shell (possibly even to
        a remote host).

        Args:
            ip: IP address to inject into the mounted raw image loop.
            hostname: Host name to inject into the mounted raw image loop.
            host: Optional host on which to execute this external call.
        """
        hostString = f'ssh {host} ' if host else ''
        loop = []
        try:
            await self._getIO(hostString + f'zfs clone {self.machineImage} {self.datasetName}')
            loop = await self._getIO(hostString + f'losetup -fvP --show /{self.datasetName}/root.raw')
            await self._getIO(hostString + f'mount {loop[0]}p1 {env["REMOTE_LOOP_MOUNTPOINT"]}')
            await self._getIO(hostString + f'\'echo "    address {ip}" >> {env["REMOTE_LOOP_MOUNTPOINT"]}/etc/network/interfaces\'')
            await self._getIO(hostString + f'\'echo {hostname} > {env["REMOTE_LOOP_MOUNTPOINT"]}/etc/hostname\'')
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
                await self._getIO(hostString + f'umount {env["REMOTE_LOOP_MOUNTPOINT"]}')
                await self._getIO(hostString + f'losetup -d {loop[0]}')
            except ValueError:
                # We don't care if they didn't exist. Still work checking.
                pass


if __name__ == '__main__':
    from asyncio import run


    async def getResults() -> None:
        snap = 'VMPool/images/OpenVPN-network-stack@1571310605'
        dataset = 'VMPool/test-DELETE'
        dmh = DatasetManager(snap, dataset)
        call = await dmh.clone(host='root@perchost.bjd2385.com', ip='192.168.2.150', hostname='test')
        print(call)


    run(getResults())