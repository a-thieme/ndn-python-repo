# -----------------------------------------------------------------------------
# NDN Repo putfile client.
#
# @Author jonnykong@cs.ucla.edu
#         susmit@cs.colostate.edu
# @Date   2019-10-18
# -----------------------------------------------------------------------------

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import asyncio as aio
from .command_checker import CommandChecker
from ..command import RepoCommandParam, SyncParam, EmbName, RepoStatCode
from ..utils import PubSub
import logging
import multiprocessing
from ndn.app import NDNApp
from ndn.encoding import Name, NonStrictName, Component, Links
import os
import platform
from hashlib import sha256
from typing import Optional, List

class SyncClient(object):

    def __init__(self, app: NDNApp, prefix: NonStrictName, repo_name: NonStrictName):
        """
        A client to sync the repo.

        :param app: NDNApp.
        :param prefix: NonStrictName. The name of this client
        :param repo_name: NonStrictName. Routable name to remote repo.
        """
        self.app = app
        self.prefix = prefix
        self.repo_name = Name.normalize(repo_name)
        self.encoded_packets = {}
        self.pb = PubSub(self.app, self.prefix)
        self.pb.base_prefix = self.prefix

        # https://bugs.python.org/issue35219
        if platform.system() == 'Darwin':
            os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

    async def join_sync(self, sync_prefix: NonStrictName, register_prefix: NonStrictName = None,
                        data_name_dedupe: bool = False, reset: bool = False) -> bytes:

        # construct insert cmd msg
        cmd_param = RepoCommandParam()
        cmd_sync = SyncParam()
        cmd_sync.sync_prefix = sync_prefix
        cmd_sync.register_prefix = register_prefix
        cmd_sync.data_name_dedupe = data_name_dedupe
        cmd_sync.reset = reset
        
        cmd_param.sync_groups = [cmd_sync]
        cmd_param_bytes = bytes(cmd_param.encode())

        # publish msg to repo's insert topic
        await self.pb.wait_for_ready()
        is_success = await self.pb.publish(self.repo_name + Name.from_str('sync'), cmd_param_bytes)
        if is_success:
            logging.info('Published an insert msg and was acknowledged by a subscriber')
        else:
            logging.info('Published an insert msg but was not acknowledged by a subscriber')
        return sha256(cmd_param_bytes).digest()
