import yaml
from common.const import CONTROLLER_CONFIG_PATH
import sys


class EvaluationConf():

    def __init__(self):
        self.listen_port = None
        self.log_dir = None
        self.runner_data_dir = None
        self.local_host_ip = None
        self.agent_tools = {}
        self.platform_tools = {}
        self.parse()

    def parse(self):
        try:
            with open(CONTROLLER_CONFIG_PATH, 'r') as y:
                yml = yaml.safe_load(y)
                self.listen_port = yml.get('listen_port', 10083)
                self.local_host_ip = yml.get('local_host_ip', "127.0.0.1")
                self.log_dir = yml.get('log_dir', "/var/log/evaluation")
                self.runner_data_dir = yml.get(
                    'runner_data_dir', "/var/evaluation"
                )
                self.max_runner_num = yml.get('max_runner_num', 10)
                self.parse_agent_tools(yml)
                self.parse_platform_tools(yml)
                self.parse_mysql(yml)
                self.parse_redis(yml)
        except Exception as e:
            print("Yaml parser Error: %s" % e)
            sys.exit(1)

    def parse_agent_tools(self, yml):
        self.agent_tools = yml.get("agent-tools", {})

    def parse_platform_tools(self, yml):
        self.platform_tools = yml.get("platform-tools", {})

    def parse_mysql(self, yml):
        self.mysql = yml.get("mysql", {})
        self.mysql_host = self.mysql.get("host", "127.0.0.1")
        self.mysql_port = self.mysql.get("port", 3306)
        self.mysql_user = self.mysql.get("user", "root")
        self.mysql_password = self.mysql.get("password", "deepflow")
        self.mysql_db = self.mysql.get("db", "evaluation")

    def parse_redis(self, yml):
        self.redis = yml.get("redis", {})
        self.redis_host = self.redis.get("host", "127.0.0.1")
        self.redis_port = self.redis.get("port", 6379)
        self.redis_password = self.redis.get("password", "root")
        self.redis_db = self.redis.get("db", "0")

    def is_valid(self):
        return self.listen_port and self.log_dir and self.runner_data_dir


conf = EvaluationConf()
