import os
import re
import time
import datetime
import yaml
from jinja2 import Environment, BaseLoader, Undefined

from eval_lib.common import logger

log = logger.get_logger()

# from mailmerge import MailMerge

from .base import ReportBase

# key is case_name pattern, value is TEMPLATE file path and case_group abbreviations
REPORT_TEMPLATE_LIST = {
    "performance_analysis_.*": (
        "./report/templates/agent_performance_report.md",
        "performance_analysis"
    ),
}


def get_report_template(case_name):
    content = None
    for k, v in REPORT_TEMPLATE_LIST.items():
        match = re.match(k, case_name)
        if bool(match):
            file_path = v[0]
            with open(file_path, "r") as f:
                content = f.read()
            break
    return content


def get_report_index(case_name):
    template_index = None
    for k, v in REPORT_TEMPLATE_LIST.items():
        match = re.match(k, case_name)
        if bool(match):
            template_index = v[1]
            break
    return template_index


class Dict2Obj:

    def __init__(self, d):
        self.values = []
        for k, v in d.items():
            if isinstance(v, dict):
                v = Dict2Obj(v)
            if k.isdigit():
                if int(k) == len(self.values):
                    self.values.append(v)
                elif int(k) > len(self.values):
                    self.values += [""] * (len(self.values) - int(k))
                    self.values.append(v)
                elif int(k) < len(self.values):
                    self.values[int(k)] = v
            else:
                setattr(self, k, v)

    def __getitem__(self, key):
        if key < len(self.values):
            return self.values[int(key)]
        else:
            return ""

    def __getattr__(self, key):
        if key.isdigit() and key < len(self.values):
            return self.values[int(key)]
        else:
            return ""


class SilentUndefined(Undefined):

    def __str__(self):
        return ""

    def __getitem__(self, key):
        return self

    def __getattr__(self, key):
        return self


class ReportMarkdown(ReportBase):

    def __init__(self, data_path):
        self.yaml_list = []

        self.data_path = data_path
        self.report_path = f"{data_path}/markdown/"
        if os.path.exists(self.report_path):
            pass
        else:
            log.info(f"mkdir {self.report_path}")
            os.mkdir(self.report_path)

    def load_data(self):
        for file in os.listdir(self.data_path):
            if file.endswith(".yaml"):
                file_path = os.path.join(self.data_path, file)
                with open(file_path, "r") as f:
                    yaml_data = yaml.safe_load(f)
                    self.yaml_list.append(yaml_data)

    def merge(self):

        def write(data):
            report_template = get_report_template(data["case_name"])
            if report_template is None:
                return
            template_index = get_report_index(data["case_name"])
            md_template = Environment(
                loader=BaseLoader, undefined=SilentUndefined
            ).from_string(report_template)
            #md_template = Environment(loader=BaseLoader).from_string(report_template)
            data = Dict2Obj(data)
            report = md_template.render(data=data)
            report_path = f"{self.report_path}/agnet-perfromance-report-{template_index}.md"
            with open(report_path, "w") as f:
                f.write(report)

        data = {}
        for yaml_data in self.yaml_list:
            template_index = get_report_index(yaml_data["case_name"])
            if template_index not in data:
                data[template_index] = yaml_data
            else:
                data[template_index].update(yaml_data)
        for index, v in data.items():
            write(v)

    def run(self):
        try:
            flag = 0
            for file in os.listdir(self.data_path):
                if file.endswith(".yaml"):
                    flag = 1
                    break
            if flag == 0:
                return
            self.load_data()
            self.merge()
        except Exception as e:
            log.error(e)
