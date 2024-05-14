import multiprocessing
import time
import threading
import traceback
import sys
import os
import traceback

from typing import List
from multiprocessing import Process

from eval_lib.model.base import CaseParams
from eval_lib.databases.mysql.models.models import CaseRecord
from eval_lib.databases.mysql import const as db_const
from manager.runner import Runner
from eval_lib.common.logger import get_logger
from eval_lib.model.const import CASE_PARAMS_STATUS_CREATE, CASE_PARAMS_STATUS_PAUSE, CASE_PARAMS_STATUS_CANCEL, CASE_PARAMS_STATUS_RESUME
from config import conf

log = get_logger()
RUNNER_TIMEOUT = 60 * 60


class Manager(Process):

    def __init__(self, q):
        super().__init__()
        self.message_queue: multiprocessing.Queue = q
        self.runner_queue: List[Runner] = []
        self.init()

    def init(self):
        try:
            main_file_path = os.path.abspath(sys.modules['__main__'].__file__)
            os.chdir(os.path.dirname(main_file_path))
            CaseRecord.update(status=db_const.CASE_RECORD_STATUS_EXCEPTION
                              ).where(
                                  CaseRecord.status.not_in([
                                      db_const.CASE_RECORD_STATUS_FINISHED,
                                      db_const.CASE_RECORD_STATUS_ERROR,
                                      db_const.CASE_RECORD_STATUS_EXCEPTION
                                  ])
                              ).execute()
        except Exception as e:
            log.error(e)

    def run(self):
        monitor_t = threading.Thread(target=self.monitor_runner_queue)
        monitor_t.start()
        while True:
            try:
                message = self.message_queue.get()
                log.info(f"get message {vars(message)}")
                if message.status == CASE_PARAMS_STATUS_CREATE:
                    log.info(f"insert test queue: {vars(message)}")
                    self.insert(message)
                elif message.status == CASE_PARAMS_STATUS_PAUSE:
                    log.info(f"pause test queue: {vars(message)}")
                    self.pause(message)
                elif message.status == CASE_PARAMS_STATUS_CANCEL:
                    log.info(f"cancel test queue: {vars(message)}")
                    self.cancel(message)
                elif message.status == CASE_PARAMS_STATUS_RESUME:
                    log.info(f"resume test queue: {vars(message)}")
                    self.resume(message)
            except Exception as e:
                log.error(e)
                log.error(traceback.print_exc())
                time.sleep(5)

    def insert(self, params: CaseParams):
        r = Runner(params)
        self.runner_queue.append(r)
        r.start()

    def pause(self, params: CaseParams):
        for runner in self.runner_queue:
            if runner.uuid == params.uuid:
                runner.signal(runner.pause)
                break
        else:
            log.error("pause: not found runner")

    def cancel(self, params: CaseParams):
        for runner in self.runner_queue:
            if runner.uuid == params.uuid:
                runner.signal(runner.cancel)
                break
        else:
            log.error("cancel: not found runner")

    def resume(self, params: CaseParams):
        for runner in self.runner_queue:
            if runner.uuid == params.uuid:
                runner.signal(runner.resume)
                break
        else:
            log.error("resume: not found runner")

    def monitor_runner_queue(self):
        while True:
            try:
                for r in self.runner_queue:
                    if not r.is_alive():
                        pass
                    elif r.timeout(RUNNER_TIMEOUT):
                        r.cancel()
                    else:
                        continue
                    # TODO：收集结果

                    # 移除runner
                    r.remove_env()
                    self.runner_queue.remove(r)
                time.sleep(3)
            except Exception as e:
                log.error(traceback.format_exc())
                log.error(e)
                time.sleep(3)
