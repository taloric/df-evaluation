from typing import Union
from peewee import PrimaryKeyField
from peewee import Model

from ..db import db
from ....model.base import BaseStruct


class BaseModel(Model):
    id = PrimaryKeyField()

    class Meta:
        database = db

    def to_json(self):
        return {
            key.column_name.upper(): getattr(self, key.column_name, None)
            for key in self._meta.sorted_fields
        }

    @classmethod
    def visible_where_clause(cls, filter: Union[dict, BaseStruct], **kwargs):
        """
        根据提供的过滤条件生成对应的可见性 WHERE 子句。
        
        参数:
        - cls: 当前类，用于调用类级别的 where_clause 方法。
        - filter: 一个字典或 BaseStruct 实例，包含用于构建 WHERE 子句的过滤条件。
        - **kwargs: 额外的关键字参数，也可用于构建 WHERE 子句。
        
        返回值:
        - 返回一个表示 WHERE 条件的表达式，这些条件由 filter 和 kwargs 中的参数生成。
        """
        where = None
        # 遍历 filter 参数生成的 WHERE 子句，并合并为一个表达式
        for clause in cls.where_clause(filter):
            if where is None:
                where = clause
            else:
                where = (where) & clause
        # 遍历 kwargs 参数生成的 WHERE 子句，并合并到之前的表达式中
        for clause in cls.where_clause(kwargs):
            if where is None:
                where = clause
            else:
                where = (where) & clause
        return where

    @classmethod
    def where_clause(cls, filter):
        """
        根据提供的过滤条件生成对应的查询条件。

        参数:
        - cls: 类对象，用于查找属性与过滤条件匹配。
        - filter: 字典对象，包含需要应用的过滤条件。

        返回值:
        - 生成器对象，包含构建的查询条件。
        """
        for key in filter.keys():
            # 过滤条件值为空时，跳过
            if filter.get(key) is None:
                continue
            # 检查过滤条件中的键是否为类属性
            if not hasattr(cls, key):
                # 如果键以's'结尾且去掉's'后的键是类属性，则生成包含子查询条件的生成器项
                if key[-1] == "s" and hasattr(cls, key[:-1]):
                    values = filter.get(key)
                    if not isinstance(values, list):
                        values = [values]
                    yield getattr(cls, key[:-1]).in_(values)
            else:
                values = filter.get(key)
                if isinstance(values, list):
                    yield getattr(cls, key).in_(values)
                else:
                    # 为类属性生成等于过滤值的查询条件的生成器项
                    yield getattr(cls, key) == filter.get(key)
