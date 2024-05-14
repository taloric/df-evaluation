import datetime
import threading
import time
import requests
import yaml
from config import conf
from common.const import POD_MAX_ABNORMAL_STATUS_NUMBER
from eval_lib.databases.redis.runner_info import RedisRunnerInfo
from common.utils import ssh_pool_default
from eval_lib.common.logger import get_logger
from eval_lib.model.base import CaseParams
from eval_lib.databases.mysql import const as db_const
from eval_lib.databases.redis import const as redis_const
from common.mysql import update_case_record
from report.report import ReportManager
import os

ALLURE_SERVER = "http://10.1.19.19:20080"
log = get_logger()


class Runner(threading.Thread):

    def __init__(self, params: CaseParams):
        super().__init__()
        self.case_params = params
        self.uuid = params.uuid
        self.image_tag = params.runner_image_tag
        self.start_time = int(time.time())
        self.redis_db = RedisRunnerInfo(
            host=conf.redis_host, port=conf.redis_port,
            password=conf.redis_password, db=conf.redis_db, max_connections=10
        )
        self.local_host_ip = conf.local_host_ip
        self.runner_data_path = f"{conf.runner_data_dir}/runner-{self.uuid}"
        self.release_name = f"runner-{self.uuid[:8]}"
        self.callback = None
        self.signal_lock = threading.Lock()

    def signal(self, input=None):
        """
        处理信号回调函数的设置和获取。
        
        :param input: 指定一个新的回调函数，如果提供，则替换当前的回调函数。
        :type input: function
        :return: 如果设置了回调函数且此次调用未提供新的回调函数，则返回当前的回调函数；否则返回None。
        """
        with self.signal_lock:  # 确保设置或获取回调函数时的线程安全
            if input is not None:  # 设置新的回调函数
                self.callback = input
                return None
            else:  # 获取当前的回调函数
                return self.callback

    def run(self):

        # TODO: leyi 更新更多信息
        update_case_record(
            self.uuid, status=db_const.CASE_RECORD_STATUS_STARTING
        )
        self.create_data_dir()
        self.exec_env()

        self.wait()

        update_case_record(
            self.uuid, status=db_const.CASE_RECORD_STATUS_STOPPING
        )
        self.get_results()

        update_case_record(
            self.uuid, status=db_const.CASE_RECORD_STATUS_FINISHED
        )

    def exec_env(self):
        # TODO: leyi 创建pod, 写入redis
        runner_yaml_path = f"{self.runner_data_path}/{self.release_name}.yaml"
        self.create_runner_yaml_file(runner_yaml_path)
        cmds = [
            "helm repo update evaluation",
            f"helm install {self.release_name} evaluation/evaluation-runner -n evaluation --create-namespace -f {runner_yaml_path}",
        ]
        ssh_client = ssh_pool_default.get(self.local_host_ip)
        try:
            for cmd in cmds:
                _, stdout, stderr = ssh_client.exec_command(cmd)
                output = stdout.read().decode()
                error = stderr.read().decode()
                if error:
                    log.error(f"exec cmd {cmd} error: {error}")
                    return
                log.info(f"exec cmd {cmd} output: {output}")
        except Exception as e:
            log.error(f"exec_env: error: {e}")
        # redis 添加信息
        self.redis_db.init_runner_info(uuid=self.uuid)
        time.sleep(10)

    def check_runner_pod_running(self):
        command = f"kubectl get pod -n evaluation |grep {self.release_name}-evaluation-runner "
        ssh_client = ssh_pool_default.get(self.local_host_ip)
        _, stdout, _ = ssh_client.exec_command(command)
        output = stdout.read().decode()
        if "Running" in output:
            return True
        else:
            return False

    def check_runner_pod_completed(self):
        runner_info = self.redis_db.get_runner_info(uuid=self.uuid)
        if runner_info["runner-status"] == redis_const.CASE_STATUS_COMPLETED:
            return True
        else:
            return False

    def wait(self):
        """
        等待测试用例执行完成。
        此函数会周期性地检查 Runner Pod 的状态，直到 Pod 运行完成或达到最大异常状态次数。
        如果检测到 Runner Pod 完成运行，则会记录执行状态并返回。
        如果 Runner Pod 未完成运行且存在回调函数，则会调用回调函数。
        如果 Runner Pod 的状态长时间未就绪，则会记录错误状态并抛出异常。
        """
        log.info("wait for case execution to complete")
        count = 0
        runner_started = False
        while count < POD_MAX_ABNORMAL_STATUS_NUMBER:
            # 检查 Runner Pod 是否正在运行
            if not self.check_runner_pod_running():
                time.sleep(10)
                count += 1
                if runner_started:
                    # 如果测试用例已经开始执行，但当前检测到未运行，则将其状态更新为待定，并重置开始标志
                    update_case_record(
                        self.uuid, status=db_const.CASE_RECORD_STATUS_PENDING
                    )
                    runner_started = False
                continue

            if not runner_started:
                # 当检测到 Runner Pod 开始运行时，更新用例记录为执行中状态
                update_case_record(
                    self.uuid, status=db_const.CASE_RECORD_STATUS_STARTED
                )
                runner_started = True

            # 检查 Runner Pod 是否已完成执行
            if not self.check_runner_pod_completed():
                # 如果 Runner Pod 未完成执行，且存在回调函数，则调用回调函数
                callback = self.signal()
                if callback is not None:
                    callback()
                    self.callback = None
                time.sleep(5)
                continue
            else:
                # 如果 Runner Pod 完成执行，记录相关信息并返回
                log.info(
                    f"case exec finished, runner_status: {self.redis_db.get_runner_info(uuid=self.uuid)}"
                )
                return

        # 如果达到最大异常状态次数，更新用例记录为错误状态，并抛出异常
        update_case_record(self.uuid, status=db_const.CASE_RECORD_STATUS_ERROR)
        log.error("runner pod status not ready")
        raise Exception("runner pod status not ready")

    def remove_env(self):
        # TODO: leyi 删除pod
        command = f"helm uninstall {self.release_name} -n evaluation"
        ssh_client = ssh_pool_default.get(self.local_host_ip)
        try:
            _, _, stderr = ssh_client.exec_command(command)
            error = stderr.read().decode()
            if error:
                log.error(f"uninstall env {self.release_name} error: {error}")
                # raise
            self.redis_db.delete_runner_info(uuid=self.uuid)
        except Exception as e:
            log.error(f"remove_env: error: {e}")

    def cancel(self):
        # TODO: leyi 中断当前执行,立即生成结果
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_STOPPING
        )
        self.redis_db.cancel_case(uuid=self.uuid)
        log.info("cancel case")
        self.wait_case_sync()
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_FINISHED
        )

    def pause(self):
        # TODO: leyi 暂停当前执行
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_PAUSING
        )
        self.redis_db.pause_case(uuid=self.uuid)
        log.info("pause case")
        # TODO：leyi 检查是否完成暂停
        self.wait_case_sync()
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_PAUSED
        )

    def resume(self):
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_STARTING
        )
        self.redis_db.resume_case(uuid=self.uuid)
        log.info("resume case")
        self.wait_case_sync()
        update_case_record(
            uuid=self.uuid, status=db_const.CASE_RECORD_STATUS_STARTED
        )

    def timeout(self, timeout: int) -> bool:
        if time.time() - self.start_time > timeout:
            return True
        return False

    def wait_case_sync(self):
        while True:
            time.sleep(5)
            runner_info = self.redis_db.get_runner_info(uuid=self.uuid)
            if runner_info["case-control-status"] == runner_info[
                "case-status"] or runner_info[
                    "case-status"] == redis_const.CASE_STATUS_COMPLETED:
                break

    def create_data_dir(self):
        self.runner_report_path = f"{self.runner_data_path}/report"
        self.runner_log_path = f"{self.runner_data_path}/log"
        self.runner_allure_path = f"{self.runner_data_path}/allure-result"
        self.runner_tmp = f"{conf.runner_data_dir}/tmp"
        log.info(f"data_dir is : {self.runner_data_path}")
        folder_paths = [
            self.runner_report_path,
            self.runner_log_path,
            self.runner_allure_path,
            self.runner_tmp,
        ]
        for folder_path in folder_paths:
            try:
                os.makedirs(folder_path)
                log.info(f"Runner {self.uuid} create folder: {folder_path}")
            except FileExistsError:
                pass

    def create_runner_yaml_file(self, file_path):
        helm_value_dict = {}
        runner_config_dict = {}
        runner_config_dict["case_params"] = self.case_params.to_json()
        runner_config_dict["redis"] = conf.redis
        runner_config_dict["mysql"] = conf.mysql
        runner_config_dict["listen_port"] = conf.listen_port
        runner_config_dict["agent-tools"] = conf.agent_tools
        runner_config_dict["platform-tools"] = conf.platform_tools
        runner_config_dict["runner_data_dir"] = conf.runner_data_dir
        helm_value_dict["runnerConfig"] = runner_config_dict
        helm_value_dict["image"] = {"tag": self.image_tag}
        with open(file_path, 'w') as file:
            yaml.dump(helm_value_dict, file)
        if not os.path.exists(file_path):
            log.error(f"file :{file_path} not found")

    def get_results(self):
        self.push_allure_results()
        self.get_performance_results()

    def get_performance_results(self):
        files_name = os.listdir(self.runner_report_path)
        for file_name in files_name:
            if file_name.endswith('.yaml'):
                break
        else:
            return
        log.info("generate test report")
        try:
            # TODO: luyao 查看是否收到performance文件，收到则生成报告
            rm = ReportManager(
                report_path=self.runner_report_path, report_engines=None
            )
            rm.run()
        except Exception as e:
            log.error(f"get performance results error: {e}")

    def push_allure_results(self):
        #TODO: luyao 查看是否收到allure压缩包，收到则发送
        allure_file_zip = f"{self.runner_allure_path}/allure-report.zip"
        if not os.path.exists(allure_file_zip):
            return
        headers = {"accept": "*/*"}
        files = {
            'allureReportArchive': (
                "allure-report.zip", open(allure_file_zip,
                                          'rb'), 'application/x-zip-compressed'
            )
        }
        current_timestamp = int(time.time())
        result_url = ALLURE_SERVER + "/api/report/" + self.uuid + "-" + str(
            current_timestamp
        )[-7:]
        try:
            resp = requests.post(result_url, files=files, headers=headers)
            log.info(resp.text)
            if resp.status_code == 201:
                return resp.json()
            else:
                log.error("Unknown Error !!!")
        except Exception as e:
            log.error(f"upload allure file error: {e}")
            return False
