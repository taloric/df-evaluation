import pytest
import allure,time
from common.utils import step as allure_step
from common.utils import choose_platform
from common.utils import choose_agent
from eval_lib.common.logger import get_logger
from common.results import AgentResults
from common import utils as common_utils
from case.performance_analysis import utils as performance_analysis_utils
from platform_tools.aliyun import ali_const
from common.utils import ssh_pool_default

log = get_logger()

case_name = "performance_analysis_nginx_http_with_agent"
case_info = {}

def create_http_traffic_action(
    nginx_ip, wrk_ip, param
):
    ssh = ssh_pool_default.get(wrk_ip)
    start_time = int(time.time())
    log.info("start generating http traffic")
    _, _, stderr = ssh.exec_command(
        f'''wrk2 -c20 -t20 -R {param} -d 100  -L http://{nginx_ip}:80/index.html | grep -E "(Latency Distribution|Requests/sec)" -A 8 | grep -E "^( 50.000| 90.000|Requests/sec:)"| awk '{{print $2}}' > log'''
    )
    err = stderr.readlines()
    if err:
        log.error(f"wrk2 err, log:{err}")
    log.info("complete http traffic generation")
    end_time = int(time.time())
    return start_time, end_time

class TestPerformanceAnalysisNginxHttpWithAgent():

    @classmethod
    def setup_class(cls):
        uuid = common_utils.get_case_uuid()
        cls.instance_name_agent = f"{case_name}_agent_{uuid}"
        cls.instance_name_wrk = f"{case_name}_wrk_{uuid}"
        cls.result = AgentResults(case_name=case_name)
        cls.result.add_case_info(info=case_info)

    @classmethod
    def teardown_class(cls):
        cls.result.generate_yaml_file()

    @allure.suite('performance analysis')
    @allure.epic('Agent performance analysis')
    @allure.feature('')
    @allure.title('Agent性能分析 - http')
    @allure.description('Test the performance of the agent on the http protocol')
    @pytest.mark.medium
    def test_performance_analysis_nginx_http_with_agent(self):
        with allure_step('step 1: create instance'):
            platform = choose_platform()
            instance_info = platform.create_instances(
                instance_names=[self.instance_name_agent,self.instance_name_wrk],
                image_id=ali_const.ali_image_id_performance_analysis,
            )
        agent_ip = instance_info[self.instance_name_agent]
        wrk_ip = instance_info[self.instance_name_wrk]
        with allure_step('step 2: install agent'):
            agent = choose_agent(agent_ip)
            agent.deploy(self.instance_name_agent)

        with allure_step('step 3: sync agent'):
            agent.start()
            agent.ensure_agent_status_available()
            agent.configure_agent()

        with allure_step('step 4: upload config and reload telegraf'):
            common_utils.upload_files(
                vm_ip=agent_ip,
                local_path="case/performance_analysis/tools/telegraf.conf",
                remote_path="/etc/telegraf/telegraf.conf",
                ssh_pool=agent.get_ssh_pool(),
            )
            performance_analysis_utils.reload_telegraf_conf(
                vm_ip=agent_ip, 
                ssh_pool=agent.get_ssh_pool()
            )
        
        with allure_step('step 5: start wrk2 traffic tool'):
            common_utils.ensure_process_running(
                vm_ip=agent_ip,
                process_name="nginx",
                ssh_pool=agent.get_ssh_pool(),
            )
            start_time, end_time = create_http_traffic_action(
                nginx_ip=agent_ip,
                wrk_ip=wrk_ip,
                param=10000,
            )
            wrk2_result_data = performance_analysis_utils.get_traffic_tool_data(
                vm_ip=wrk_ip,
            )
            self.result.add_result_data(data=wrk2_result_data)
            log.info(wrk2_result_data)

        with allure_step('step 6: get agent result'):
            monitored_process_name = ["nginx", agent.agent_process_name]
            telegraf_result_data = performance_analysis_utils.get_process_usage_by_telegraf(
                vm_ip=agent_ip,
                process_name_list=monitored_process_name,
                start_time=start_time,
                end_time=end_time,
            )
            self.result.add_result_data(data=telegraf_result_data)
            log.info(telegraf_result_data)
            agent_result_data = agent.get_metric_data_by_agent(start_time=start_time, end_time=end_time)
            # self.result.add_result_data(data=agent_result_data)
            log.info(agent_result_data)
        
        with allure_step('step 7: delete instance'):
            platform.delete_instances(
                instance_names=[self.instance_name_agent,self.instance_name_wrk]
            )


