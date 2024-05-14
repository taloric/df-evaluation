import pytest
import allure,time
from common.utils import step as allure_step
from eval_lib.common.logger import get_logger
from common.results import AgentResults

case_info={}
case_name = "performance_analysis_nginx_http_with_agent"

log = get_logger()
class TestPrint():

    @classmethod
    def setup_class(cls):
        cls.result = AgentResults(case_name=case_name)
        cls.result.add_case_info(info=case_info)
        pass

    @classmethod
    def teardown_class(cls):
        cls.result.generate_yaml_file()
        pass

    @allure.suite('performance analysis')
    @allure.epic('Agent performance analysis')
    @allure.feature('')
    @allure.title('Agent性能分析 - http')
    @allure.description('Test the performance of the agent on the http protocol')
    @pytest.mark.medium
    def test_print(self):
        result_data = {
            "agent.max_cpu": "1.2%",
            "agent.max_mem": "132MB"
            }
        with allure_step('step 1: create instance'):
            self.result.add_result_data(data=result_data)
            log.info("gogogo")
            count = 2
            for i in range(count):
                log.info(f"no {i}: test")
                time.sleep(10)
            log.info('successful')

        with allure_step('step 2: create instance'):
            log.info("gogogo")
            count = 2
            for i in range(count):
                log.info(f"no {i}: test2")
                time.sleep(10)
            log.info('successful3')
