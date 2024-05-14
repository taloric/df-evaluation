import yaml
from common.const import RUNNER_CONFIG_PATH
from eval_lib.common.ssh import SSHPool


class AgentBase(object):
    """所有采集器类的基类"""

    def __init__(self) -> None:
        self._ssh_pool = SSHPool()
        self.custom_param:dict = {}
        self.agent_process_name = ""

    def init_custom_param(self):
        with open(RUNNER_CONFIG_PATH, 'r') as file:
            data = yaml.safe_load(file)
            self.uuid = data['case_params']['uuid']
            agent_type = data['agent-tools']['type']
            self.custom_param = data['agent-tools'][agent_type]
    
    def get_ssh_pool(self):
        return self._ssh_pool

    # ----------------以下属性或方法待后代实现----------------
    def init(self, meta):
        """初始化采集器参数的函数
        :param meta: 采集器参数的元数据
        :return: 
        """
        pass

    def deploy(self, agent_name):
        pass

    def start(self):
        pass

    def stop(self):
        pass

    def release(self):
        pass

    def ensure_agent_status_available(self):
        pass

    def check_abnormal_restart_time(self, start_time, end_time) -> bool:
        pass

    def restart(self):
        pass
    
    def configure_agent(self, config_dict: dict):
        pass

    def get_metric_data_by_agent(self,start_time,end_time):
        pass   