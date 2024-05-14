import yaml
from common.const import RUNNER_CONFIG_PATH
from eval_lib.common.logger import get_logger
from eval_lib.model.base import CaseParams

log = get_logger()


class CaseConf():

    def __init__(self):
        self.agent_tools = {}
        self.platform_tools = {}
        self.runner_data_dir = None
        self.listen_port = None
        self.case_params: CaseParams = None
        self.parse()

    def parse(self):
        try:
            with open(RUNNER_CONFIG_PATH, 'r') as f:
                yml:dict = yaml.safe_load(f)
                self.listen_port = yml.get('listen_port', 10083)
                self.agent_tools = yml.get("agent-tools")
                self.platform_tools = yml.get("platform-tools")
                self.runner_data_dir = yml.get("runner_data_dir")
                self.case_params = self.parse_case_params(yml)
                self.parse_mysql(yml)
                self.parse_redis(yml)
        except Exception as e:
            log.error(f"file:eval-runner.yaml, yaml parser Error: {e}")

    def parse_case_params(self, yml: dict) -> CaseParams:
        case_params: dict = yml.get("case_params")
        return CaseParams(case_params)

    def parse_mysql(self, yml):
        self.mysql = yml.get("mysql")
        self.mysql_host = self.mysql.get("host", "127.0.0.1")
        self.mysql_port = self.mysql.get("port", 3306)
        self.mysql_user = self.mysql.get("user", "root")
        self.mysql_password = self.mysql.get("password", "deepflow")
        self.mysql_db = self.mysql.get("db", "evaluation")
        
    def parse_redis(self, yml):
        self.redis = yml.get("redis")
        self.redis_host = self.redis.get("host", "127.0.0.1")
        self.redis_port = self.redis.get("port", 6379)
        self.redis_password = self.redis.get("password", "root")
        self.redis_db = self.redis.get("db", "0")


    def is_valid(self):
        if not self.agent_tools:
            log.error("agent-tools is empty")
            assert False
        if not self.platform_tools:
            log.error("platform-tools is empty")
            assert False
        if not self.runner_data_dir:
            log.error("runner_data_dir is empty")
            assert False
        if not self.case_params:
            log.error("case_params is empty")
            assert False
        if not self.case_params.is_valid():
            log.error(f"case_params {self.case_params} is invalid")
            assert False
        return True


conf = CaseConf()
