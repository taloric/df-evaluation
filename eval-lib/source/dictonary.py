from ..model import const as model_const
from ..databases.mysql import const as db_const


# 元类，构造字典映射
class DictionaryMeta(type):

    def __new__(cls, name, bases, dct):
        mappings = {}
        for k, v in dct.items():
            if k.endswith("_DICTONARY"):
                mappings[k] = v
        dct['__mappings__'] = mappings
        return super().__new__(cls, name, bases, dct)


class Dictionary(metaclass=DictionaryMeta):
    """
    字典映射
    """

    CASE_DICTIONARY = {
        # [测试例名称，测试例路径，测试例中文名称]
        "performance_analysis_nginx_http": [
            "performance_analysis/test_performance_analysis_nginx_http.py",
            "性能分析-极端高性能场景(nginx)"
        ],
    }

    CASE_GROUP_DICTIONARY = {
        # [测试例组名称， 测试例组路径， 测试例组中文名称]
        "performance_analysis": ["performance_analysis", "性能分析"],
    }
    CASE_STATUS_SUPPORT_UPDATE_DICTIONARY = {
        # [测试例修改状态int，名称，所在哪些状态时支持更新]
        model_const.CASE_PARAMS_STATUS_PAUSE: [
            "pause", [db_const.CASE_RECORD_STATUS_STARTED]
        ],
        model_const.CASE_PARAMS_STATUS_CANCEL: [
            "cancel",
            [
                db_const.CASE_RECORD_STATUS_STARTED,
                db_const.CASE_RECORD_STATUS_PAUSED
            ]
        ],
        model_const.CASE_PARAMS_STATUS_RESUME: [
            "resume", [db_const.CASE_RECORD_STATUS_PAUSED]
        ],
    }
    CASE_STATUS_DICTIONARY = {
        db_const.CASE_RECORD_STATUS_INIT: ["Init"],
        db_const.CASE_RECORD_STATUS_STARTING: ["Starting"],
        db_const.CASE_RECORD_STATUS_STARTED: ["Running"],
        db_const.CASE_RECORD_STATUS_PENDING: ["Pending"],
        db_const.CASE_RECORD_STATUS_PAUSED: ["Paused"],
        db_const.CASE_RECORD_STATUS_PAUSING: ["Pausing"],
        db_const.CASE_RECORD_STATUS_FINISHED: ["Finished"],
        db_const.CASE_RECORD_STATUS_STOPPING: ["Stopping"],
        db_const.CASE_RECORD_STATUS_ERROR: ["Error"],
        db_const.CASE_RECORD_STATUS_EXCEPTION: ["Exception"],
    }
