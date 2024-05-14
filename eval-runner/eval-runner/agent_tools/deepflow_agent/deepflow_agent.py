import yaml, os, time
import copy
from datetime import datetime, timedelta
from common.module import AgentMeta
from agent_tools.base import AgentBase
from agent_tools.deepflow_agent import url
from agent_tools.deepflow_agent.deepflow_server import DeepflowServer
from common import utils as common_utils
from eval_lib.common.logger import get_logger

log = get_logger()


class DeeepflowAgent(AgentBase):

    def __init__(self):
        super().__init__()
        self.deepflow_server = DeepflowServer()
        self.agent_name: str = None
        self.vtap_lcuuid: str = None
        self.agent_process_name: str = "deepflow-agent"

    def init(self, meta: AgentMeta):
        """初始化采集器参数的函数
        :param meta: 采集器参数的元数据
        :return: 
        """
        self._ssh_pool.default_port = meta.ssh_port
        self._ssh_pool.default_username = meta.ssh_username
        self._ssh_pool.default_password = meta.ssh_password
        self.agent_ip = meta.agent_ip
        self.agent_version = meta.version
        self.init_custom_param()

    def deploy(self, agent_name):
        # 初始化deepflow_server
        server_ip = self.custom_param.get("server_ip", None)
        if server_ip is None:
            log.error("deepflow_server_ip is None")
            assert False
        self.deepflow_server.init(
            server_ip,
            self.custom_param.get("server_ssh_port", 22),
            self.custom_param.get("server_ssh_username"),
            self.custom_param.get("server_ssh_password"),
        )
        # 部署agent
        self.agent_name = agent_name
        if self.custom_param["agent_type"] == "k8s":
            self.deploy_k8s_agent()
        elif self.custom_param["agent_type"] == "workload":
            self.deploy_workload_agent()

    def deploy_k8s_agent(self):
        """部署k8s类型采集器
        通过sealos 安装k8s
        """
        common_utils.install_k8s(
            vm_ip=self.agent_ip,
            ssh_pool=self._ssh_pool,
        )
        common_utils.upload_files(
            vm_ip=self.agent_ip,
            local_path="agent_tools/deepflow_agent/file/deepflow-agent.yaml",
            remote_path="/root/",
            ssh_pool=self._ssh_pool,
        )
        ssh_client = self._ssh_pool.get(self.agent_ip)
        ssh_client.exec_command(
            f"sed -i '2i\  tag: {self.agent_version}' deepflow-agent.yaml"
        )
        version = ""
        if "v6.2" in self.agent_version:
            version = "--version 6.2.6"
        elif "v6.3" in self.agent_version:
            version = "--version 6.3.9"
        elif "v6.4" in self.agent_version:
            version = "--version 6.4.9"
        cluster_id = self.deepflow_server.cloud_add_subdomain(
            vpc_name=self.custom_param["k8s_type_params"].get(
                "vpc_name", "infrastructure"
            ),
            domain_name=self.custom_param["k8s_type_params"].get(
                "domain_name", "aliyun"
            ),
            subdomain_name=self.agent_name,
        )
        cmd_list = [
            "helm repo add deepflow-agent https://deepflow-ce.oss-cn-beijing.aliyuncs.com/chart/stable",
            "helm repo update deepflow-agent",
            f'''helm install deepflow-agent -n deepflow deepflow-agent/deepflow-agent {version} --create-namespace \
                --set deepflowServerNodeIPS={{{self.deepflow_server.server_ip}}} --set deepflowK8sClusterID={cluster_id} -f deepflow-agent.yaml'''
        ]
        cmd = " && ".join(cmd_list)
        _, stdout, stderr = ssh_client.exec_command(cmd)
        log.info(f"Install agent by k8s cmd: {cmd}")
        logs = stdout.readlines()
        if logs and 'deepflow-agent Host listening port:' in logs[-1]:
            log.info('Deploy the deepflow-agent successfully in kubernetes')
        else:
            log.error(
                f"Deploy the deepflow-agent failed, logs is {stderr.read().decode()}"
            )
            assert False

    def deploy_workload_agent(self):
        """部署workload类型采集器
        """
        ssh_client = self._ssh_pool.get(self.agent_ip)
        system_name, system_version = common_utils.get_system_info(
            vm_ip=self.agent_ip,
            ssh_pool=self._ssh_pool,
        )
        common_utils.install_unzip(self.agent_ip, self._ssh_pool)
        if 'CentOS' in system_name:
            agent_url = url.deepflow_agent_rpm_lastest_url.replace(
                "latest", self.agent_version
            )
            install_cmd = f'''curl -O {agent_url} &&\
                                unzip deepflow-agent-rpm.zip &&\
                                rpm -ivh x86_64/deepflow-agent-1*.rpm
                                '''
        elif 'Ubuntu' in system_name and "14." in system_version:
            agent_url = url.deepflow_agent_deb_lastest_url.replace(
                "latest", self.agent_version
            )
            install_cmd = f'''curl -O {agent_url} &&\
                                unzip deepflow-agent-deb.zip &&\
                                dpkg -i x86_64/deepflow-agent-*.upstart.deb
                                '''
        elif 'Ubuntu' in system_name and "14." not in system_version:
            agent_url = url.deepflow_agent_deb_lastest_url.replace(
                "latest", self.agent_version
            )
            install_cmd = f'''curl -O {agent_url} &&\
                                unzip deepflow-agent-deb.zip &&\
                                dpkg -i x86_64/deepflow-agent-*.systemd.deb
                                '''
        elif 'Debian' in system_name:
            agent_url = url.deepflow_agent_deb_lastest_url.replace(
                "latest", self.agent_version
            )
            install_cmd = f'''curl -O {agent_url} &&\
                                unzip deepflow-agent-deb.zip &&\
                                dpkg -i x86_64/deepflow-agent-*.systemd.deb
                                '''
        elif 'Anolis' in system_name:
            agent_url = url.deepflow_agent_arm_rpm_lastest_url.replace(
                "latest", self.agent_version
            )
            install_cmd = f'''curl -O {agent_url} &&\
                                unzip deepflow-agent*.zip &&\
                                rpm -ivh aarch64/deepflow-agent-1*.rpm
                                '''
        else:
            log.error(f'Unsupported system: {system_name}')
            assert False
        _, stdout, stderr = ssh_client.exec_command(install_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            log.info(
                f"deepflow-agent is installation successful. please start it"
            )
        else:
            log.error(
                f"deepflow-agent is installation failed. err: {stderr.read().decode()}"
            )
            assert False
        server_ip = self.deepflow_server.server_ip
        bind_cmd = f"sed -i 's/  - 127.0.0.1/  - {server_ip}/g' /etc/deepflow-agent.yaml"
        _, stdout, stderr = ssh_client.exec_command(bind_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            log.info(
                f"deepflow-agent bind server successful, server_ip is {server_ip}"
            )
        else:
            log.error(
                f"deepflow-agent bind server failed. err: {stderr.read().decode()}"
            )
            assert False

    def release(self):
        ssh_client = self._ssh_pool.get(self.agent_ip)
        system_name, _ = common_utils.get_system_info(
            vm_ip=self.agent_ip,
            ssh_pool=self._ssh_pool,
        )
        uninstall_cmd = ""
        if 'CentOS' in system_name:
            uninstall_cmd = "rpm -e deepflow-agent"
        elif 'Ubuntu' in system_name:
            uninstall_cmd = "dpkg -r deepflow-agent"
        elif 'Debian' in system_name:
            uninstall_cmd = "dpkg -r deepflow-agent"
        elif 'Amolis' in system_name:
            uninstall_cmd = "rpm -e deepflow-agent"
        else:
            log.error(f'Unsupported system: {system_name}')
            return
        _, stdout, stderr = ssh_client.exec_command(uninstall_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            log.info('deepflow-agent uninstalled successfully on')
        else:
            log.error(
                f'failed to install deepflow-agent on {stderr.read().decode()}'
            )

    def start(self):
        if self.custom_param["agent_type"] == "k8s":
            log.info("k8s agent start is not supported")
            return
        ssh_client = self._ssh_pool.get(self.agent_ip)
        check_cmd = 'systemctl start deepflow-agent && systemctl status deepflow-agent'
        _, stdout, stderr = ssh_client.exec_command(check_cmd)
        output = stdout.read().decode()
        if "Active: active (running)" in output:
            log.info("deepflow agent successfully started and is running")
            return True
        else:
            log.error(
                f"deepflow-agent start failed, err: {stderr.read().decode()}"
            )
            return False

    def stop(self):
        if self.custom_param["agent_type"] == "k8s":
            log.info("k8s agent stop is not supported")
            return
        ssh_client = self._ssh_pool.get(self.agent_ip)
        check_cmd = 'systemctl stop deepflow-agent && systemctl status deepflow-agent'
        _, stdout, stderr = ssh_client.exec_command(check_cmd)
        output = stdout.read().decode()
        if "Active: inactive (dead)" in output:
            log.info("deepflow agent successfully stopped")
            return True
        else:
            log.error(
                f"deepflow-agent stop failed, err: {stderr.read().decode()}"
            )
            return False

    def restart(self):
        if self.custom_param["agent_type"] == "k8s":
            log.info("k8s agent restart is not supported")
            return
        ssh_client = self._ssh_pool.get(self.agent_ip)
        check_cmd = 'systemctl restart deepflow-agent && systemctl status deepflow-agent'
        _, stdout, stderr = ssh_client.exec_command(check_cmd)
        output = stdout.read().decode()
        if "Active: active (running)" in output:
            log.info(f"deepflow agent restarted successfully and is running")
            return True
        else:
            log.error(
                f"deepflow-agent restart failed, err: {stderr.read().decode()}"
            )
            return False

    def ensure_agent_status_available(self):
        self.vtap_lcuuid = self.deepflow_server.check_vtaps_list_by_ip(
            agent_ip=self.agent_ip
        )
        self.deepflow_server.check_analyzer_ip(agent_ip=self.agent_ip)

    def check_abnormal_restart_time(self, start_time, end_time) -> bool:
        """ 检查采集器在特定时间是否出现了重启
        :param start_time: 开始时间戳
        :param end_time: 结束时间戳
        :return: True or False, True表示出现了重启，False表示没有出现重启。
        """
        if self.custom_param["agent_type"] == "k8s":
            log.info("k8s agent check abnormal restart time is not supported")
            return
        ssh_client = self._ssh_pool.get(self.agent_ip)
        _, stdout, _ = ssh_client.exec_command(
            ''' grep restart /var/log/deepflow-agent/deepflow-agent.log  \
                |awk '{log.info substr($1, index($1, "2024")),$2}' '''
        )
        # 这里需要把时间转换为时间戳，然后判断时间戳是否在指定的时间范围内
        for line in stdout:
            line = line.strip()
            if not line:
                continue
            time_str = line.split(' ')[0]
            # 日志时间是北京时间，需要减去8小时，才能转换为时间戳。
            time_obj = datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S.%f'
                                         ) - timedelta(hours=8)
            time_stamp = int(time_obj.timestamp())
            if start_time <= time_stamp <= end_time:
                log.warning(f"deepflow-agent restarted at {time_str}")
                return True
        log.info(f"deepflow-agent did not restart")
        return False

    def configure_agent(
        self, config_dict: dict=None
    ):
        """ 配置采集器
        :param config_dict: 自定义配置
        :return: 
        """
        server_ip = self.deepflow_server.server_ip
        ssh_client = self.deepflow_server._ssh_pool.get(server_ip)
        tmp_file_path = ""
        group_name = "deepflow_group_{}".format(
            self.agent_name.replace("-", "_")
        )
        if config_dict is None:
            config_dict = {}
        else:
            config_dict = copy.deepcopy(config_dict)
        try:
            existing_data = {"vtap_group_id": ""}
            if "config" in self.custom_param:
                # 读取env.yaml的配置
                existing_data.update(self.custom_param["config"])
            existing_data.update(config_dict)
            tmp_file_path = f'{group_name}_tmp.yaml'
            with open(tmp_file_path, 'w') as file:
                yaml.dump(existing_data, file)
        except Exception as e:
            log.error(f"Error: {repr(e)}")
        common_utils.upload_files(
            vm_ip=self.deepflow_server.server_ip,
            local_path=tmp_file_path,
            remote_path=f'/root/{group_name}.yaml',
            ssh_pool=self._ssh_pool,
        )
        os.remove(tmp_file_path)
        agent_group_id = self.deepflow_server.create_group_with_exist_agent(
            group_name=group_name, vtap_lcuuid=self.vtap_lcuuid
        )
        # 通过deepflow-ctl载入配置
        config_cmd = [
            f"sed -i '/vtap_group_id:/s/.*/vtap_group_id: {agent_group_id}/g' {group_name}.yaml",
            f"deepflow-ctl agent-group-config create -f {group_name}.yaml"
        ]
        config_cmd = " && ".join(config_cmd)
        _, stdout, stderr = ssh_client.exec_command(config_cmd)
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            log.info(f"deepflow-agent configure successful")
        else:
            log.error(
                f"deepflow-agent configure failed  {stderr.read().decode()}"
            )
            assert False
        time.sleep(120)

    def get_metric_data_by_agent(self, start_time, end_time):
        vtap_info={}
        vtap_full_name = self.deepflow_server.get_vtap_full_name_by_ip(
            self.agent_ip
        )
        max_cpu = self.deepflow_server.get_vtap_max_cpu_usage(
            vtap_full_name, start_time, end_time
        )
        max_mem = self.deepflow_server.get_vtap_max_mem_usage(
            vtap_full_name, start_time, end_time
        )
        vtap_info = {
            "agent.max_cpu": max_cpu,
            "agent.max_mem": max_mem,
        }
        
        return vtap_info
