import time
import os
import subprocess
import sys
import shutil

from common import const
from common.config import conf
from eval_lib.common.logger import get_logger
from eval_lib.common.logger import LoggerManager
from common.utils import redis_db
from common.utils import zip_dir
from eval_lib.databases.redis import const as redis_const
from common.client import ResultClient, LogClient

log = get_logger()


class Runner():

    def __init__(self):
        self.uuid = conf.case_params.uuid
        self.case_params = conf.case_params
        self.start_time = int(time.time())
        self.pytest_process: subprocess.Popen = None

        self.runner_dir = const.LOCAL_PATH
        self.runner_data_path = f"{conf.runner_data_dir}/runner-{self.uuid}"
        self.runner_report_path = f"{self.runner_data_path}/report"
        self.runner_log_path = f"{self.runner_data_path}/log"
        self.runner_allure_path = f"{self.runner_data_path}/allure-result"

    def run(self):
        self.init_env()
        self.exec_pytest()
        self.wait()
        # self.get_results()
        self.push_results()
        redis_db.update_runner_info(
            uuid=self.uuid,
            info={"runner-status": redis_const.CASE_STATUS_COMPLETED}
        )
        time.sleep(300)

    def init_env(self):
        """初始化环境目录
        """
        # 创建数据目录
        log.info(f"data_dir is : {self.runner_data_path}")
        folder_paths = [
            conf.runner_data_dir,
            self.runner_data_path,
            self.runner_report_path,
            self.runner_log_path,
            self.runner_allure_path,
        ]
        for folder_path in folder_paths:
            try:
                os.makedirs(folder_path)
                log.info(f"Runner {self.uuid} create folder: {folder_path}")
            except FileExistsError:
                pass
        log.info(f"Runner {self.uuid} init env success.")

    def exec_pytest(self):
        # 执行测试用例
        envs = os.environ.copy()
        envs["PYTHONPATH"] = f":{self.runner_dir}"
        # TODO: leyi 修改log文件
        log_path = f"{self.runner_log_path}/pytest-{self.uuid}.log"
        command = f"pytest -vs ./case/{self.case_params.case_name}  --alluredir {self.runner_allure_path} --workers {self.case_params.process_num} > {log_path}"
        try:
            # 执行 pytest 命令
            log.info(f"exec pytest command: {command}")
            self.pytest_process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.runner_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=envs,
            )
        except subprocess.CalledProcessError as e:
            log.error("exec pytest error:", e)

        redis_db.update_runner_info(
            uuid=self.uuid,
            info={
                "runner-status": redis_const.CASE_STATUS_RUNNING,
                "case-status": redis_const.CASE_STATUS_RUNNING
            }
        )

    def wait(self):
        log_path = f"{self.runner_log_path}/pytest-{self.uuid}.log"
        lc = self.start_forward_log(log_path=log_path)
        while True:
            # 检查进程状态
            time.sleep(5)
            # pytest 进程结束了
            if self.pytest_process.poll() is not None:
                if self.pytest_process.returncode == 0:
                    log.info("pytest process has finished.")
                else:
                    _, pytest_stderr = self.pytest_process.communicate()
                    log.error("pytest process occurred error")
                    if pytest_stderr is not None:
                        log.error(f"error_log: {pytest_stderr.decode()}")
                lc.stop()
                redis_db.update_runner_info(
                    uuid=self.uuid,
                    info={"case-status": redis_const.CASE_STATUS_COMPLETED}
                )
                break
            runner_info_dict = redis_db.get_runner_info(uuid=self.uuid)
            if runner_info_dict["case-control-status"] == redis_const.CASE_STATUS_CANCELLED:
                # 主动取消case执行
                redis_db.update_runner_info(
                    uuid=self.uuid,
                    info={
                        "case-status": redis_const.CASE_STATUS_CANCELLED
                    }
                )
                log.error("case cancelled")
                self.interrupt()
                lc.stop()
                break

    def interrupt(self):
        # TODO: leyi 中断当前执行,立即生成结果
        self.pytest_process.kill()
        log.error(f"Runner {self.uuid} interrupt.")

    def start_forward_log(self, log_path):
        log.info("start log forwarding")
        server_url = f"http://{const.CONTROLLER_HOST}:{conf.listen_port}{const.API_PREFIX_RESULT_LOG}"
        lc = LogClient(
            uuid=self.uuid,
            log_file=log_path,
            server_url=server_url
        )
        lc.setDaemon(True)
        lc.start()
        return lc

    def push_results(self):
        #TODO: luyao 压缩self.runner_data_path，发送到controller
        log.info("start push result to controller")
        runner_data_zip = f"runner-{self.uuid}.zip"
        shutil.move(
            src=f"{conf.runner_data_dir}/runner.log",
            dst=f"{self.runner_log_path}/runner.log"
        )
        zip_dir(
            folder_path=self.runner_data_path,
            output_path=runner_data_zip
        )
        server_url = f"http://{const.CONTROLLER_HOST}:{conf.listen_port}{const.API_PREFIX_RESULT_ZIP}"
        rc = ResultClient(server_url=server_url)
        rc.send_result_zip(zip_file_path=runner_data_zip)
        log.info(f"Runner {self.uuid} push results.")

    def get_results(self):
        # TODO: luyao 收集测试结果
        log.info("start gengerate allure result")
        allure_tmp_dir = "allure-report"
        command = f"allure generate -c {self.runner_allure_path}/ -o {allure_tmp_dir}"
        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=self.runner_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if process.returncode == 0:
                log.info("allure-report file gengerate successful")
            else:
                log.error(
                    f"allure-report file gengerate failed: error: {process.stderr.decode()}"
                )
                return False
        except subprocess.CalledProcessError:
            log.error("allure generate error, cmd error")
            return False
        zip_dir(
            folder_path="allure-report",
            output_path=f"{self.runner_allure_path}/allure-report.zip"
        )


if __name__ == '__main__':
    if not conf.is_valid():
        print('Invalid conf value, error exit.')
        sys.exit(1)
    # TODO: 初始化log文件
    LoggerManager(log_file=f"{conf.runner_data_dir}/runner.log")
    Runner().run()
