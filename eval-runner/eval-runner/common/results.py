import yaml
from common.config import conf
class ResultsBase:
    pass


class AgentResults(ResultsBase):

    def __init__(self, case_name):
        self.case_name = case_name
        # results dir
        self.dir_path =  f"{conf.runner_data_dir}/runner-{conf.case_params.uuid}/report"  
        self.data_dict = {"case_name": case_name}
        
    def add_result_data(self, data: dict, index: int=0):
        modified_dict = {f"{self.case_name}." + key.replace("-", "_") + f".{index}": value for key, value in data.items()}
        self.data_dict.update(modified_dict)
    
    def add_case_info(self, info):
        self.data_dict.update(info)

    def generate_yaml_file(self):
        if len(self.data_dict) > 1:
            yaml_data = yaml.dump(self.format_data(self.data_dict))
            with open(f"{self.dir_path}/{self.case_name}.yaml", "w") as f:
                f.write(yaml_data)

    @staticmethod
    def format_data(data):

        def merge_dict(dict1, dict2):
            result = {}
            for key in set(dict1.keys()) | set(dict2.keys()):
                if key in dict1 and key in dict2 and isinstance(
                    dict1[key], dict
                ) and isinstance(dict2[key], dict):
                    result[key] = merge_dict(dict1[key], dict2[key])
                else:
                    result[key] = dict2.get(key, dict1.get(key))
            return result

        result = {}
        for key, value in data.items():
            point = {}
            parts = key.split(".")
            for i in range(len(parts) - 1, -1, -1):
                if i == len(parts) - 1:
                    point[parts[i]] = value
                else:
                    point = {parts[i]: point}
            result = merge_dict(result, point)
        return result
