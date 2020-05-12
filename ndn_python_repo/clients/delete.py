"""
    NDN Repo delete client.

    @Author jonnykong@cs.ucla.edu
    @Date   2019-09-26
"""

import os
import sys
sys.path.insert(1, os.path.join(sys.path[0], '..'))

import argparse
import asyncio as aio
from ..command.repo_commands import RepoCommandParameter, RepoCommandResponse
from .command_checker import CommandChecker
from ..utils import PubSub
import logging
from ndn.app import NDNApp
from ndn.encoding import Name, Component, DecodeError, NonStrictName
from ndn.types import InterestNack, InterestTimeout
from ndn.utils import gen_nonce


class DeleteClient(object):
    """
    This client deletes specified data packets stored at a remote repo.
    """
    def __init__(self, app: NDNApp, prefix: NonStrictName, repo_name: NonStrictName):
        """
        :param app: NDNApp.
        :param repo_name: NonStrictName. Routable name to remote repo.
        """
        self.app = app
        self.prefix = prefix
        self.repo_name = repo_name
        self.pb = PubSub(self.app, self.prefix)

    async def delete_file(self, prefix, start_block_id: int=None, end_block_id: int=None):
        """
        Delete data packets between [<name_at_repo>/<start_block_id>, <name_at_repo>/<end_block_id>]
        from the remote repo.

        :param prefix: NonStrictName. The name with which this file is stored in the repo.
        :param start_block_id: int.
        :param end_block_id: int.
        :return: number of deleted packets.
        """
        # Send command interest
        cmd_param = RepoCommandParameter()
        cmd_param.name = prefix
        cmd_param.start_block_id = start_block_id
        cmd_param.end_block_id = end_block_id
        process_id = gen_nonce()
        cmd_param.process_id = process_id
        cmd_param_bytes = cmd_param.encode()

        # publish msg to repo's delete topic
        await self.pb.wait_for_ready()
        self.pb.publish(self.repo_name + ['delete'], cmd_param_bytes)

        # wait until repo delete all data
        return await self.wait_for_finish(process_id)

    async def wait_for_finish(self, process_id: int):
        """
        Send delete check interest wait until delete process completes

        :param process_id: int. The process id to check for delete process
        :return: number of deleted packets.
        """
        checker = CommandChecker(self.app)
        n_retries = 3
        while n_retries > 0:
            response = await checker.check_delete(self.repo_name, process_id)
            if response is None:
                logging.info(f'Response code is None')
                await aio.sleep(1)
            # might receive 404 if repo has not yet processed delete command msg
            elif response.status_code == 404:
                n_retries -= 1
                logging.info(f'Response code is {response.status_code}')
                await aio.sleep(1)
            elif response.status_code == 300:
                logging.info(f'Response code is {response.status_code}')
                await aio.sleep(1)
            elif response.status_code == 200:
                logging.info('Delete process {} status: {}, delete_num: {}'
                             .format(process_id, response.status_code, response.delete_num))
                return response.delete_num
            else:
                # Shouldn't get here
                assert False