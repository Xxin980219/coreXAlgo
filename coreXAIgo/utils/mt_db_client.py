from typing import Dict, List, Optional, Union

import pandas as pd
from sqlalchemy import create_engine, text, CursorResult, Engine

from sqlalchemy.exc import SQLAlchemyError


class MtDBClient:
    """
    轻量级多数据库查询客户端（仅实现查询功能）

    支持多种数据库连接管理，提供简洁的查询接口，自动处理连接池和资源清理。
    适用于需要从多个数据库执行查询操作的场景。
    """

    def __init__(self, db_configs: Dict[str, dict]):
        """
        初始化多数据库客户端实例

        Args:
            db_configs (Dict[str, dict]): 数据库配置字典，格式为：
                {
                    "db_name1": {
                        "host": "主机地址",
                        "port": 端口号,
                        "user": "用户名",
                        "password": "密码",
                        "database": "数据库名",
                        "charset": "字符集"  # 可选，默认utf8mb4
                    },
                    "db_name2": {...}
                }

        Example:
            >>> configs = {
            ...     "user_db": {
            ...         "host": "localhost",
            ...         "port": 3306,
            ...         "user": "root",
            ...         "password": "123456",
            ...         "database": "user_management"
            ...     }
            ... }
            >>> client = MtDBClient(configs)
        """
        if not db_configs or not isinstance(db_configs, dict):
            raise ValueError("数据库配置不能为空且必须为字典类型")

        self._configs = db_configs
        self._engines = {}  # 数据库引擎缓存 {db_name: engine_instance}

    def _get_engine(self, db_name: str) -> Engine:
        """
        获取或创建指定数据库的SQLAlchemy引擎

        Args:
            db_name (str): 目标数据库名称，必须在初始化配置中定义

        Returns:
            Engine: SQLAlchemy数据库引擎实例
        """
        if db_name not in self._configs:
            raise ValueError(f"未知数据库: {db_name}，可用数据库: {list(self._configs.keys())}")

        # 如果引擎已存在，直接返回
        if db_name in self._engines:
            return self._engines[db_name]

        try:
            config = self._configs[db_name]
            # 构建数据库连接URL
            url = (f"mysql+pymysql://{config['user']}:{config['password']}@"
                   f"{config['host']}:{config.get('port', 3306)}/"
                   f"{config['database']}?charset={config.get('charset', 'utf8mb4')}")

            # 创建带连接池的引擎
            engine = create_engine(
                url,
                pool_size=5,  # 连接池保持的连接数
                max_overflow=10,  # 连接池最大溢出连接数
                pool_timeout=30,  # 获取连接的超时时间（秒）
                pool_recycle=3600,  # 连接回收时间（秒）
                pool_pre_ping=True,  # 执行前ping检测连接有效性
                isolation_level="AUTOCOMMIT"  # 自动提交模式，适合查询操作
            )

            self._engines[db_name] = engine
            return engine

        except Exception as e:
            raise RuntimeError(f"创建数据库[{db_name}]引擎失败: {e}")

    def query(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            fetchone: bool = False
    ) -> Union[List[dict], dict, None]:
        """
        执行SQL查询并返回结果

        Args:
            db_name (str): 目标数据库名称
            sql (str): SQL查询语句，支持参数化查询
            params (Optional[Union[tuple, dict]], optional): 查询参数，可以是元组（位置参数）或字典（命名参数）
            fetchone (bool, optional): 是否只返回第一行结果，默认为False返回所有结果

        Returns:
            Union[List[dict], dict, None]: 查询结果：
                - fetchone=False: 返回包含所有行的字典列表
                - fetchone=True: 返回单行字典或None（无结果时）

        Example:
            >>> # 查询所有用户
            >>> users = client.query("user_db", "SELECT * FROM users WHERE age > :age", {"age": 18})
            >>>
            >>> # 查询单个用户
            >>> user = client.query("user_db", "SELECT * FROM users WHERE id = :id", {"id": 1}, fetchone=True)
        """
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL语句不能为空且必须为字符串")

        engine = self._get_engine(db_name)

        try:
            with engine.connect() as connection:
                # 使用text()包装SQL以支持参数绑定和防止SQL注入
                stmt = text(sql)

                # 执行查询
                result: CursorResult = connection.execute(stmt, params or {})

                # 转换结果
                if fetchone:
                    row = result.fetchone()
                    return dict(row._mapping) if row else None
                else:
                    return [dict(row._mapping) for row in result]

        except SQLAlchemyError as e:
            raise RuntimeError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")
        except Exception as e:
            raise RuntimeError(f"执行查询时发生未知错误: {e}")

    def query_to_dataframe(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            chunk_size: Optional[int] = None
    ) -> pd.DataFrame:
        """
        执行查询并将结果转换为pandas DataFrame

        Args:
            db_name (str): 目标数据库名称
            sql (str): SQL查询语句
            params (Optional[Union[tuple, dict]], optional): 查询参数
            chunk_size (Optional[int], optional): 分块大小，指定时返回迭代器，用于处理大型数据集

        Returns:
            pd.DataFrame: 包含查询结果的DataFrame，保持原始数据类型

        Example:
            >>> # 读取整个表到DataFrame
            >>> df = client.query_to_dataframe("user_db", "SELECT * FROM users")
            >>>
            >>> # 分块读取大型数据集
            >>> df_chunks = client.query_to_dataframe("log_db", "SELECT * FROM access_logs", chunk_size=10000)
        """
        engine = self._get_engine(db_name)

        try:
            # 使用pandas直接读取SQL查询结果
            df = pd.read_sql_query(
                sql=sql,
                con=engine,
                params=params,
                chunksize=chunk_size
            )

            # 如果指定了分块大小，需要合并所有块
            if chunk_size is not None:
                df = pd.concat(df, ignore_index=True)

            return df

        except Exception as e:
            raise RuntimeError(f"数据库[{db_name}]查询转换为DataFrame失败: {e}\nSQL: {sql}")
        finally:
            # 确保连接正确关闭
            engine.dispose()

    def _close_all(self):
        """关闭所有数据库连接并清理资源"""
        for db_name, engine in self._engines.items():
            try:
                engine.dispose()
            except Exception as e:
                print(f"关闭数据库[{db_name}]连接时出错: {e}")

        self._engines.clear()

    def __del__(self):
        """析构函数，自动清理资源"""
        self._close_all()

    def list_databases(self) -> List[str]:
        """
        获取所有已配置的数据库名称列表

        Returns:
            List[str]: 所有可用的数据库名称列表
        """
        return list(self._configs.keys())