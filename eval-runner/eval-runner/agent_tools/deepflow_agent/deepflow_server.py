from eval_lib.common.logger import get_logger
from eval_lib.common.ssh import SSHPool
from agent_tools.deepflow_agent import url
import time, requests
import json
from urllib.parse import urlencode

log = get_logger()


class DeepflowServer():

    def __init__(self) -> None:
        self.server_ip = None
        self.control_port = None
        self.query_port = None
        self._ssh_pool = SSHPool()

    def init(
        self, server_ip, ssh_port=22, ssh_username=None, ssh_password=None
    ):
        """初始化控制器参数的函数
        :param meta: 控制器参数的元数据
        :return: 
        """
        self._ssh_pool.default_port = ssh_port
        self._ssh_pool.default_username = ssh_username
        self._ssh_pool.default_password = ssh_password
        self.server_ip = server_ip
        self.control_port = self.get_control_port()
        self.query_port = self.get_query_port()

    def get_control_port(self, server_ip=None, retry_count=100):
        server_ip = server_ip if server_ip else self.server_ip
        ssh_client = self._ssh_pool.get(server_ip)
        for _ in range(retry_count):
            try:
                log.info("Getting controller port")
                _, stdout, stderr = ssh_client.exec_command(
                    '''kubectl get svc -n deepflow | grep -o "20417:[0-9]*" | cut -d ":" -f 2
                    ''', timeout=10
                )
                control_port = stdout.readline().strip()
                if control_port:
                    log.info(f"Control port: {control_port}")
                    self.control_port = control_port
                    return control_port
            except Exception as e:
                log.error(
                    f"stderr: {stderr.read().decode('utf-8')}, Failed to get port: {e}"
                )
                time.sleep(3)
        log.error("Failed to get control port after retrying.")
        return None

    def get_query_port(self, server_ip=None, retry_count=100):
        server_ip = server_ip if server_ip else self.server_ip
        ssh_client = self._ssh_pool.get(server_ip)
        for _ in range(retry_count):
            try:
                log.info("Getting querier port")
                _, stdout, stderr = ssh_client.exec_command(
                    '''kubectl get svc -n deepflow | grep -o "20416:[0-9]*" | cut -d ":" -f 2
                    ''', timeout=10
                )
                query_port = stdout.readline().strip()
                if query_port:
                    log.info(f"Query port: {query_port}")
                    self.query_port = query_port
                    return query_port
            except Exception as e:
                log.error(
                    f"stderr: {stderr.read().decode('utf-8')}, Failed to get port: {e}"
                )
                time.sleep(3)
        log.error("Failed to get query port after retrying.")
        return None

    def create_group_with_exist_agent(self, group_name="", vtap_lcuuid=""):
        '''Move the agent to the specified group
        return: group_id
        '''
        headers = {'Content-Type': 'application/json'}
        url = "http://{}:{}/v1/vtap-groups/".format(
            self.server_ip, self.control_port
        )
        data = {"NAME": group_name, "VTAP_LCUUIDS": [vtap_lcuuid]}
        log.info(f"Data to be sent: {data}")
        try:
            response = requests.post(url=url, headers=headers, json=data)
            response_json: dict = response.json()
            log.info("Response JSON: {}".format(response_json))
            agent_group_id = response_json["DATA"]["SHORT_UUID"]
            if response_json.get(
                "OPT_STATUS"
            ) == "SUCCESS" and agent_group_id:
                return agent_group_id
            else:
                log.error(
                    f"Failed to add group with existing agent: {response_json}"
                )
                assert False
        except Exception as e:
            log.error(f"Failed to add group with existing agent: {e}")
            assert False

    def check_vtaps_list_by_ip(self, agent_ip, retry_count=15) -> str:
        '''Loop to check if vtaps_list contains vtap by ip of vtap.
        :param retry_count: required, number of checks
        :param agent_ip: ip of agent
        :return VTAP_LCUUID
        '''
        for _ in range(retry_count):
            log.info('Waiting for vtaps synchronization, about 60s')
            try:
                check_url = f"{url.protocol}{self.server_ip}:{self.control_port}{url.vtaps_api_prefix}"
                response = requests.get(url=check_url)
                last_vtaps_list = response.json().get('DATA', [])
                for vt in last_vtaps_list:
                    if vt.get('LAUNCH_SERVER') == agent_ip:
                        log.info(
                            f'The vtap was synchronized successfully, the ip is {agent_ip}'
                        )
                        return vt['LCUUID']
            except Exception as err:
                log.error(
                    f'Error occurred during vtaps synchronization check: {err}'
                )
            time.sleep(60)
        log.error(f'vtaps synchronization failure, the ip is {agent_ip}')
        log.error(f'Last vtaps list: {last_vtaps_list}')
        assert False

    def check_analyzer_ip(self, agent_ip, retry_count=30):
        ssh_client = self._ssh_pool.get(self.server_ip)
        check_cmd = "deepflow-ctl agent list|grep %s|awk '{print $5}'|xargs -I {} deepflow-ctl trisolaris.check --cip %s --cmac {} config|grep analyzer_ip|grep %s" % (
            agent_ip, agent_ip, self.server_ip
        )
        for i in range(retry_count):
            _, stdout, stderr = ssh_client.exec_command(check_cmd)
            logs = stdout.readlines()
            errs = stderr.readlines()
            if len(logs) > 0:
                log.info(f"successfully assign analyzer_ip, logs is {logs}")
                break
            log.info(f"Have been waiting for {10 * i} seconds")
            if errs:
                log.info(errs)
            time.sleep(10)
        else:
            log.error("Timeout! agent not assigned analyzer_ip")
            assert False

    def get_vtap_full_name_by_ip(self, agent_ip):
        '''Get vtap_full_name by the ip of the vtaps
        :param agent_ip: required, The ip of vtaps
        '''
        try:
            vtaps_url = f"{url.protocol}{self.server_ip}:{self.control_port}{url.vtaps_api_prefix}"
            response = requests.get(url=vtaps_url)
            # 检查异常响应状态 4xx or 5xx
            response.raise_for_status()

            json_data = response.json().get('DATA', [])
            for vt in json_data:
                if vt.get('LAUNCH_SERVER') == agent_ip:
                    return vt['NAME']

            log.error(
                f"Failed to get vtap name for IP: {agent_ip}. No matching entry found."
            )
            assert False
        except requests.exceptions.RequestException as e:
            log.error(f"Error occurred while fetching vtap information: {e}")
            assert False

    def get_vtap_max_cpu_usage(self, vtap_full_name, start_time, end_time):
        '''Maximum CPU usage of the agent on DF by API. Parameter description:
        vtap_full_name; required field, Name of vtaps
        start_time; required field, Start time for filtering data
        end_time; required field, End time for filtering data
        '''
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        sql = '''select Max(`metrics.cpu_percent`) AS RSS, `tag.host` from \
                deepflow_agent_monitor where `tag.host` IN ('%s') AND time>=%s \
                AND time<=%s group by `tag.host` limit 100''' % (
            vtap_full_name, start_time, end_time
        )
        data = {'db': 'deepflow_system', 'sql': sql}
        data = urlencode(data, encoding='gb2312')
        response = requests.post(
            url='http://%s:%s/v1/query/' % (self.server_ip, self.query_port),
            headers=headers, data=data
        )
        # 检查异常响应状态 4xx or 5xx
        response.raise_for_status()
        log.info(
            f"get_vtap_max_cpu_usage:: sql:{sql} res: {response.content}"
        )
        result = response.json().get('result', {})
        values = result.get('values', [])
        if not values:
            log.error('No data found in the response.')
            assert False
        max_cpu = max([float(i[-1]) for i in values])
        max_cpu_percentage = "{:.2f}%".format(float(max_cpu))
        return max_cpu_percentage

    def get_vtap_max_mem_usage(self, vtap_full_name, start_time, end_time):
        '''Maximum memory usage of the agent on DF by API. Parameter description:
        vtaps_name; required field, Name of vtaps
        start_time; required field, Start time for filtering data
        end_time; required field, End time for filtering data
        '''
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        sql = '''select Max(`metrics.memory`) AS RSS, `tag.host` from \
                deepflow_agent_monitor where `tag.host` IN ('%s') AND time>=%s \
                AND time<=%s group by `tag.host` limit 100''' % (
            vtap_full_name, start_time, end_time
        )
        data = {'db': 'deepflow_system', 'sql': sql}
        data = urlencode(data, encoding='gb2312')
        response = requests.post(
            url='http://%s:%s/v1/query/' % (self.server_ip, self.query_port),
            headers=headers, data=data
        )
        # 检查异常响应状态 4xx or 5xx
        response.raise_for_status()
        log.info(
            f"get_vtap_max_mem_usage:: sql:{sql} res: {response.content}"
        )
        result = response.json().get('result', {})
        values = result.get('values', [])
        max_mem = max([float(i[-1]) for i in values])
        # B -> MB
        max_mem_Mb = "{:.2f}Mb".format(float(max_mem) / 1024 / 1024)
        return max_mem_Mb

    def cloud_add_subdomain(self, vpc_name, domain_name, subdomain_name):
        '''
        Cloud platform add a subdomain 
        return: cluster_id
        '''
        vpc_lcuuid = self.get_vpc_lcuuid_by_name(vpc_name)
        domain_lcuuid = self.get_domain_lcuuid_by_name(domain_name)
        cluster_id = self.add_subdomain_agent_sync(
            vpc_lcuuid, domain_lcuuid, subdomain_name
        )
        return cluster_id
    
    def get_vpc_lcuuid_by_name(self, vpc_name, retries=50):
        vpc_info_list = []
        for _ in range(retries):
            vpc_info_list = []
            try:
                vpc_url_for_get = f"http://{self.server_ip}:{self.control_port}{url.v2_vpcs_api_prefix}"
                res = requests.get(url=vpc_url_for_get)
                if res.status_code == 200:
                    log.info('get vpc list successfully')
                    vpc_info_list = res.json()['DATA']
                else:
                    log.error(f"get vpc list failed, res: {res.content}")
            except Exception as e:
                log.error(f"Failed to get vpc info list: {e}")
            for vpc_info in vpc_info_list:
                if vpc_name in vpc_info['NAME']:
                    vpc_lcuuid = vpc_info['LCUUID']
                    log.info(
                        f'get vpc lcuuid by name, lcuuid:{vpc_lcuuid}'
                    )
                    return vpc_lcuuid
            log.info(
                'vpc info is being synchronized, wait 10s'
            )
            time.sleep(10)
        log.error(
            f"get vpc lcuuid by name error:: vpc_info_list:{vpc_info_list}, vpc_name: {vpc_name}"
        )
        return None

    def get_domain_lcuuid_by_name(self, domain_name, retries=50):
        domain_info_list = []
        for _ in range(retries):
            domain_info_list = []
            try:
                domain_url_for_get = f"http://{self.server_ip}:{self.control_port}{url.v2_domains_api_prefix}"
                res = requests.get(url=domain_url_for_get)
                if res.status_code == 200:
                    log.info('get domain list successfully')
                    domain_info_list = res.json()['DATA']
                else:
                    log.error(f"get domain list failed, res: {res.content}")
            except Exception as e:
                log.error(f"Failed to get domain info list: {e}")
            for domain_info in domain_info_list:
                if domain_name in domain_info['NAME']:
                    domain_lcuuid = domain_info['LCUUID']
                    log.info(
                        f'get domain lcuuid by name, lcuuid:{domain_lcuuid}'
                    )
                    return domain_lcuuid
            log.info(
                'domain info is being synchronized, wait 10s'
            )
            time.sleep(10)
        log.error(
            f"get domain lcuuid by name error:: domain_info_list:{domain_info_list}, domain_name: {domain_name}"
        )
        return None
    
    def add_subdomain_agent_sync(self, vpc_lcuuid, domain_lcuuid, subdomain_name):
        subdomain_url = f"http://{self.server_ip}:{self.control_port}{url.v2_subdomains_api_prefix}"
        data = {
            "NAME": "{}".format(subdomain_name),
            "CONFIG": {
                "vpc_uuid": "{}".format(vpc_lcuuid),
                "pod_net_ipv4_cidr_max_mask": 16,
                "pod_net_ipv6_cidr_max_mask": 64,
                "port_name_regex": "^(cni|flannel|cali|vxlan.calico|tunl|en[ospx]|eth)"
            },
            "DOMAIN": "{}".format(domain_lcuuid)
        }
        data = json.dumps(data)
        header = {'content-type': 'application/json'}
        res = requests.post(
            url=subdomain_url, data=data, headers=header
        )
        log.info(f"add subdomain, res: {res.content}")
        if res.status_code == 200:
            subdomain_info = res.json()['DATA']
            cluster_id = subdomain_info['CLUSTER_ID']
            log.info(
                f'add subdomain successfully, vpc_lcuuid:{vpc_lcuuid}, domain_lcuuid:{vpc_lcuuid}, cluster_id:{cluster_id}'
            )
            return cluster_id
        else:
            log.error('add subdomain failed')
            assert False
