from typing import Dict, List, Optional, Union

import pandas as pd
import pymysql
from sqlalchemy import create_engine, text, CursorResult

__all__ = ['MtDBClient']

from sqlalchemy.exc import SQLAlchemyError


class MtDBClient:
    """轻量级多数据库查询客户端（仅实现查询功能）"""

    def __init__(self, db_configs: Dict[str, dict]):
        """
        初始化多数据库客户端
        :param db_configs: 数据库配置字典 {db_name: {host,port,user,password,database,...}}
        """
        self._configs = db_configs
        self._engines = {}  # 缓存引擎实例

    def _get_engine(self, db_name: str):
        """获取或创建SQLAlchemy引擎"""
        if (db_name not in self._engines) and (db_name not in self._configs):
                raise ValueError(f"未知数据库: {db_name}")

        config = self._configs[db_name]
        url = f"mysql+pymysql://{config['user']}:{config['password']}@{config['host']}/{config['database']}?charset={config.get('charset', 'utf8mb4')}"
        self._engines[db_name] = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_timeout=30,
                pool_recycle=3600,
                isolation_level="AUTOCOMMIT"  # 查询专用连接自动提交
        )
        return self._engines[db_name]

    def query(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            fetchone: bool = False
    ) -> Union[List[dict], dict, None]:
        """
        执行查询并自动关闭连接
        :param db_name: 目标数据库名称
        :param sql: SQL语句
        :param params: 参数（元组或字典）
        :param fetchone: 是否只返回第一行
        :return: 查询结果（列表或单行字典）
        """
        engine = self._get_engine(db_name)
        try:
            with engine.connect() as connection:
                # 使用text()包装SQL以支持参数绑定
                stmt = text(sql)

                # 执行查询
                result: CursorResult = connection.execute(stmt, params or {})

                # 获取结果
                if fetchone:
                    row = result.fetchone()
                    return dict(row._mapping) if row else None
                else:
                    return [dict(row._mapping) for row in result]

        except SQLAlchemyError as e:
            raise RuntimeError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")

    def query_to_dataframe(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            chunk_size: Optional[int] = 10000
    ) -> pd.DataFrame:
        """
        执行查询并返回pandas DataFrame
        :param db_name: 目标数据库名称
        :param sql: SQL语句
        :param params: 参数（元组或字典）
        :param chunk_size: 分块大小，用于处理大数据集
        :return: 包含查询结果的DataFrame
        """
        if db_name not in self._configs:
            raise ValueError(f"未知数据库: {db_name}")

        engine = self._get_engine(db_name)
        try:
            # 使用pandas直接读取SQL查询结果
            df = pd.read_sql_query(sql, engine, params=params, chunksize=chunk_size)

            # 如果指定了chunk_size，返回的是迭代器，我们将其合并为一个DataFrame
            if chunk_size is not None:
                df = pd.concat(df, ignore_index=True)

            return df
        except pymysql.Error as e:
            raise RuntimeError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")
        finally:
            engine.dispose()  # 关闭所有连接池连接
