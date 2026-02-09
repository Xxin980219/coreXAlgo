from typing import Dict, List, Optional, Union, Iterator, Any

import os
import time
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# 类型别名
DBConfig = Dict[str, Any]
EngineCache = Dict[str, Engine]
QueryCache = Dict[str, tuple]

# 自定义异常类
class DatabaseError(Exception):
    """数据库操作异常基类"""
    pass

class ConnectionError(DatabaseError):
    """数据库连接异常"""
    pass

class QueryError(DatabaseError):
    """数据库查询异常"""
    pass

class TransactionError(DatabaseError):
    """数据库事务异常"""
    pass


class MtDBClient:
    """
    轻量级多数据库查询客户端（仅支持查询操作）

    支持多种数据库连接管理，提供简洁的查询接口，自动处理连接池和资源清理。
    适用于需要从多个数据库执行查询操作的场景，不支持数据修改操作。

    Features:
        - ✅ 多数据库支持（MySQL、PostgreSQL、SQLite等）
        - ✅ 连接池管理和自动重连
        - ✅ 查询结果缓存
        - ✅ 数据导出
        - ✅ 表结构操作
        - ✅ 详细的错误处理和日志
        - ✅ 上下文管理器支持
    """

    def __init__(self, db_configs: Dict[str, DBConfig], logger: Optional[logging.Logger] = None, 
                 warm_up: bool = False, enable_cache: bool = False, cache_ttl: int = 300):
        """
        初始化多数据库客户端实例

        Args:
            db_configs (Dict[str, DBConfig]): 数据库配置字典，格式为：
                {
                    "db_name1": {
                        "host": "主机地址",
                        "port": 端口号,
                        "user": "用户名",
                        "password": "密码",
                        "password_env": "环境变量名",  # 从环境变量获取密码
                        "database": "数据库名",
                        "charset": "字符集",  # 可选，默认utf8mb4
                        "driver": "mysql+pymysql",  # 数据库驱动，可选
                        "ssl": {},  # SSL配置，可选
                    },
                    "db_name2": {...}
                }
            logger (Optional[logging.Logger]): 日志记录器，默认使用内置日志器
            warm_up (bool): 是否在初始化时预热连接池，默认False
            enable_cache (bool): 是否启用查询结果缓存，默认False
            cache_ttl (int): 缓存过期时间（秒），默认300秒

        Example:
            >>> configs = {
            ...     "user_db": {
            ...         "host": "localhost",
            ...         "port": 3306,
            ...         "user": "root",
            ...         "password_env": "DB_PASSWORD",  # 从环境变量获取密码
            ...         "database": "user_management"
            ...     }
            ... }
            >>> client = MtDBClient(configs, warm_up=True, enable_cache=True)
        """
        if not db_configs or not isinstance(db_configs, dict):
            raise ValueError("数据库配置不能为空且必须为字典类型")

        self._configs = db_configs
        self._engines: EngineCache = {}  # 数据库引擎缓存 {db_name: engine_instance}
        self._logger = logger or logging.getLogger(__name__)
        self._enable_cache = enable_cache
        self._cache_ttl = cache_ttl
        self._query_cache: QueryCache = {}  # 查询缓存 {cache_key: (result, timestamp)}
        
        # 连接预热
        if warm_up:
            self._warm_up_connections()
    
    def _warm_up_connections(self):
        """
        预热数据库连接池
        
        为每个配置的数据库创建连接并执行简单查询，确保连接池初始化完成
        """
        for db_name in self._configs:
            try:
                start_time = time.time()
                engine = self._get_engine(db_name)
                # 执行简单查询测试连接
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                execution_time = time.time() - start_time
                self._logger.debug(f"连接预热成功: {db_name} (耗时: {execution_time:.3f}s)")
            except Exception as e:
                self._logger.warning(f"连接预热失败: {db_name} - {e}")

    def _get_engine(self, db_name: str) -> Engine:
        """
        获取或创建指定数据库的SQLAlchemy引擎

        Args:
            db_name (str): 目标数据库名称，必须在初始化配置中定义

        Returns:
            Engine: SQLAlchemy数据库引擎实例

        Raises:
            ConnectionError: 数据库连接失败时抛出
        """
        if db_name not in self._configs:
            raise ValueError(f"未知数据库: {db_name}，可用数据库: {list(self._configs.keys())}")

        # 如果引擎已存在，直接返回
        if db_name in self._engines:
            return self._engines[db_name]

        try:
            config = self._configs[db_name].copy()
            
            # 从环境变量获取密码
            if 'password_env' in config:
                password_env = config['password_env']
                password = os.environ.get(password_env)
                if password:
                    config['password'] = password
                    self._logger.debug(f"从环境变量获取密码: {password_env}")
                else:
                    self._logger.warning(f"环境变量 '{password_env}' 未设置，使用配置中的密码")
            
            # 验证必要参数
            required_params = ['user', 'password', 'host', 'database']
            for param in required_params:
                if param not in config:
                    raise ValueError(f"数据库配置缺少必要参数: {param}")
            
            # 构建数据库连接URL
            driver = config.get('driver', 'mysql+pymysql')
            port = config.get('port', 3306)
            charset = config.get('charset', 'utf8mb4')
            
            # 根据数据库类型构建不同的连接URL
            if driver.startswith('mysql'):
                url = (f"{driver}://{config['user']}:{config['password']}@"
                       f"{config['host']}:{port}/"
                       f"{config['database']}?charset={charset}")
            elif driver.startswith('postgresql'):
                url = (f"{driver}://{config['user']}:{config['password']}@"
                       f"{config['host']}:{config.get('port', 5432)}/"
                       f"{config['database']}")
            elif driver.startswith('sqlite'):
                url = f"{driver}:///{config['database']}"
            else:
                # 默认使用MySQL格式
                url = (f"{driver}://{config['user']}:{config['password']}@"
                       f"{config['host']}:{port}/"
                       f"{config['database']}")

            # 连接参数
            connect_args = {}
            if config.get('ssl'):
                connect_args['ssl'] = config['ssl']
                self._logger.debug(f"启用SSL连接: {db_name}")

            # 创建带连接池的引擎
            engine = create_engine(
                url,
                pool_size=config.get('pool_size', 10),  # 连接池保持的连接数
                max_overflow=config.get('max_overflow', 20),  # 连接池最大溢出连接数
                pool_timeout=config.get('pool_timeout', 60),  # 获取连接的超时时间（秒）
                pool_recycle=config.get('pool_recycle', 1800),  # 连接回收时间（秒）
                pool_pre_ping=True,  # 执行前ping检测连接有效性
                isolation_level=config.get('isolation_level', "AUTOCOMMIT"),  # 隔离级别
                connect_args=connect_args
            )

            self._engines[db_name] = engine
            self._logger.debug(f"创建数据库引擎成功: {db_name}")
            return engine

        except OperationalError as e:
            raise ConnectionError(f"数据库[{db_name}]连接失败: {e}")
        except Exception as e:
            raise ConnectionError(f"创建数据库[{db_name}]引擎失败: {e}")

    def query(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            fetchone: bool = False,
            max_retries: int = 3,
            use_cache: Optional[bool] = None
    ) -> Union[List[dict], dict, None]:
        """
        执行SQL查询并返回结果

        Args:
            db_name (str): 目标数据库名称
            sql (str): SQL查询语句，支持参数化查询
            params (Optional[Union[tuple, dict]], optional): 查询参数，可以是元组（位置参数）或字典（命名参数）
            fetchone (bool, optional): 是否只返回第一行结果，默认为False返回所有结果
            max_retries (int, optional): 最大重试次数，默认为3次
            use_cache (Optional[bool], optional): 是否使用查询缓存，默认使用全局配置

        Returns:
            Union[List[dict], dict, None]: 查询结果：
                - fetchone=False: 返回包含所有行的字典列表
                - fetchone=True: 返回单行字典或None（无结果时）

        Raises:
            QueryError: 查询执行失败时抛出

        Example:
            >>> # 查询所有用户
            >>> users = client.query("user_db", "SELECT * FROM users WHERE age > :age", {"age": 18})
            >>>
            >>> # 查询单个用户
            >>> user = client.query("user_db", "SELECT * FROM users WHERE id = :id", {"id": 1}, fetchone=True)
            >>>
            >>> # 使用缓存查询
            >>> user = client.query("user_db", "SELECT * FROM users WHERE id = :id", {"id": 1}, use_cache=True)
        """
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL语句不能为空且必须为字符串")

        # 确定是否使用缓存
        should_use_cache = use_cache if use_cache is not None else self._enable_cache
        
        # 生成缓存键
        cache_key = None
        if should_use_cache:
            cache_key = f"{db_name}:{sql}:{str(params)}:{fetchone}"
            # 检查缓存
            cached_result = self._get_cached_result(cache_key)
            if cached_result is not None:
                self._logger.debug(f"使用缓存结果: {cache_key[:100]}...")
                return cached_result

        engine = self._get_engine(db_name)
        retry_count = 0

        while retry_count < max_retries:
            try:
                start_time = time.time()
                with engine.connect() as connection:
                    # 使用text()包装SQL以支持参数绑定和防止SQL注入
                    stmt = text(sql)

                    # 执行查询
                    result = connection.execute(stmt, params or {})

                    # 转换结果
                    if fetchone:
                        row = result.fetchone()
                        query_result = dict(row._mapping) if row else None
                    else:
                        query_result = [dict(row._mapping) for row in result]

                execution_time = time.time() - start_time
                self._logger.debug(f"查询执行时间: {execution_time:.4f}s, SQL: {sql[:200]}...")

                # 缓存结果
                if should_use_cache and cache_key:
                    self._cache_result(cache_key, query_result)

                return query_result

            except OperationalError as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** (retry_count - 1)  # 指数退避
                    self._logger.warning(f"查询失败 (尝试 {retry_count}/{max_retries}): {e}\n等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    # 重置引擎，强制重新连接
                    if db_name in self._engines:
                        del self._engines[db_name]
                else:
                    raise QueryError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")
            except SQLAlchemyError as e:
                raise QueryError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")
            except Exception as e:
                raise QueryError(f"执行查询时发生未知错误: {e}")
    
    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        获取缓存的查询结果
        
        Args:
            cache_key (str): 缓存键
            
        Returns:
            Optional[Any]: 缓存的结果或None
        """
        if cache_key in self._query_cache:
            result, timestamp = self._query_cache[cache_key]
            current_time = time.time()
            if current_time - timestamp < self._cache_ttl:
                return result
            else:
                # 缓存过期，删除
                del self._query_cache[cache_key]
                self._logger.debug(f"缓存过期: {cache_key[:100]}...")
        return None
    
    def _cache_result(self, cache_key: str, result: Any):
        """
        缓存查询结果
        
        Args:
            cache_key (str): 缓存键
            result (Any): 查询结果
        """
        self._query_cache[cache_key] = (result, time.time())
        # 清理过期缓存，防止内存泄漏
        self._clean_expired_cache()
    
    def _clean_expired_cache(self):
        """
        清理过期的缓存项
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self._query_cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del self._query_cache[key]
        if expired_keys:
            self._logger.debug(f"清理过期缓存: {len(expired_keys)} 项")

    def query_to_dataframe(
            self,
            db_name: str,
            sql: str,
            params: Optional[Union[tuple, dict]] = None,
            chunk_size: Optional[int] = None,
            dtype: Optional[Dict[str, Any]] = None,
            columns: Optional[List[str]] = None,
            max_retries: int = 3
    ) -> Union[pd.DataFrame, Iterator[pd.DataFrame]]:
        """
        执行查询并将结果转换为pandas DataFrame

        Args:
            db_name (str): 目标数据库名称
            sql (str): SQL查询语句
            params (Optional[Union[tuple, dict]], optional): 查询参数
            chunk_size (Optional[int], optional): 分块大小，指定时返回迭代器，用于处理大型数据集
            dtype (Optional[Dict[str, Any]], optional): 列数据类型字典，提高类型推断准确性
            columns (Optional[List[str]], optional): 要读取的列列表，减少内存使用
            max_retries (int, optional): 最大重试次数，默认为3次

        Returns:
            Union[pd.DataFrame, Iterator[pd.DataFrame]]: 
                - chunk_size=None: 返回包含查询结果的DataFrame
                - chunk_size!=None: 返回DataFrame迭代器

        Raises:
            QueryError: 查询执行失败时抛出

        Example:
            >>> # 读取整个表到DataFrame
            >>> df = client.query_to_dataframe("user_db", "SELECT * FROM users")
            >>>
            >>> # 分块读取大型数据集
            >>> df_chunks = client.query_to_dataframe("log_db", "SELECT * FROM access_logs", chunk_size=10000)
            >>> for chunk in df_chunks:
            ...     process_chunk(chunk)
            >>>
            >>> # 指定列数据类型
            >>> dtype = {"id": int, "name": str, "created_at": "datetime64[ns]"}
            >>> df = client.query_to_dataframe("user_db", "SELECT * FROM users", dtype=dtype)
        """
        if not sql or not isinstance(sql, str):
            raise ValueError("SQL语句不能为空且必须为字符串")

        engine = self._get_engine(db_name)
        retry_count = 0

        while retry_count < max_retries:
            try:
                start_time = time.time()
                
                # 构建读取参数
                read_kwargs = {
                    "sql": sql,
                    "con": engine,
                    "params": params,
                    "chunksize": chunk_size
                }
                
                # 添加可选参数
                if dtype is not None:
                    read_kwargs["dtype"] = dtype
                
                # 如果指定了列，修改SQL语句只选择这些列
                if columns is not None and len(columns) > 0:
                    # 简单的列名处理，实际应用中可能需要更复杂的处理
                    columns_str = ", ".join([f"`{col}`" for col in columns])
                    # 尝试从SQL中提取表名并构建新的查询
                    # 这里只是一个简单的实现，实际应用中可能需要更复杂的SQL解析
                    if "SELECT" in sql.upper() and "FROM" in sql.upper():
                        # 简单替换SELECT部分
                        import re
                        sql_pattern = r"SELECT.*?FROM"
                        new_select = f"SELECT {columns_str} FROM"
                        modified_sql = re.sub(sql_pattern, new_select, sql, flags=re.IGNORECASE | re.DOTALL)
                        read_kwargs["sql"] = modified_sql
                        self._logger.debug(f"修改SQL语句只选择指定列: {columns_str}")
                
                # 使用pandas直接读取SQL查询结果
                df_result = pd.read_sql_query(**read_kwargs)

                execution_time = time.time() - start_time
                self._logger.debug(f"DataFrame查询执行时间: {execution_time:.4f}s, SQL: {sql[:200]}...")

                # 如果没有指定分块大小，返回DataFrame
                if chunk_size is None:
                    return df_result
                # 如果指定了分块大小，返回迭代器
                else:
                    return df_result

            except OperationalError as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 2 ** (retry_count - 1)  # 指数退避
                    self._logger.warning(f"查询失败 (尝试 {retry_count}/{max_retries}): {e}\n等待 {wait_time}s 后重试...")
                    time.sleep(wait_time)
                    # 重置引擎，强制重新连接
                    if db_name in self._engines:
                        del self._engines[db_name]
                else:
                    raise QueryError(f"数据库[{db_name}]查询转换为DataFrame失败: {e}\nSQL: {sql}")
            except Exception as e:
                raise QueryError(f"执行查询时发生未知错误: {e}")
        
        # 理论上不会执行到这里，但为了类型提示添加
        return pd.DataFrame()



    def _close_all(self):
        """关闭所有数据库连接并清理资源"""
        for db_name, engine in self._engines.items():
            try:
                engine.dispose()
                self._logger.debug(f"关闭数据库[{db_name}]连接")
            except Exception as e:
                self._logger.warning(f"关闭数据库[{db_name}]连接时出错: {e}")

        self._engines.clear()
        self._query_cache.clear()

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

    def list_tables(self, db_name: str) -> List[str]:
        """
        获取数据库中的所有表名

        Args:
            db_name (str): 目标数据库名称

        Returns:
            List[str]: 表名列表

        Example:
            >>> tables = client.list_tables("user_db")
            >>> print(f"数据库中有 {len(tables)} 个表: {tables}")
        """
        engine = self._get_engine(db_name)
        
        try:
            inspector = engine.inspect()
            tables = inspector.get_table_names()
            self._logger.debug(f"数据库 {db_name} 中有 {len(tables)} 个表")
            return tables
        except Exception as e:
            raise QueryError(f"获取表列表失败: {e}")

    def get_table_schema(self, db_name: str, table_name: str) -> Dict[str, Dict[str, Any]]:
        """
        获取表的结构信息

        Args:
            db_name (str): 目标数据库名称
            table_name (str): 表名

        Returns:
            Dict[str, Dict[str, Any]]: 表结构信息，键为列名，值为列的详细信息

        Example:
            >>> schema = client.get_table_schema("user_db", "users")
            >>> for column, info in schema.items():
            ...     print(f"列: {column}, 类型: {info['type']}, 是否为空: {info['nullable']}")
        """
        engine = self._get_engine(db_name)
        
        try:
            inspector = engine.inspect()
            columns = inspector.get_columns(table_name)
            schema = {}
            for column in columns:
                schema[column['name']] = {
                    'type': str(column['type']),
                    'nullable': column['nullable'],
                    'default': column['default'],
                    'autoincrement': column.get('autoincrement', False)
                }
            self._logger.debug(f"获取表 {table_name} 的结构信息成功")
            return schema
        except Exception as e:
            raise QueryError(f"获取表结构失败: {e}")

    def export_to_csv(
            self,
            db_name: str,
            sql: str,
            output_file: str,
            params: Optional[Union[tuple, dict]] = None,
            sep: str = ',',
            encoding: str = 'utf-8'
    ) -> int:
        """
        执行查询并将结果导出为CSV文件

        Args:
            db_name (str): 目标数据库名称
            sql (str): SQL查询语句
            output_file (str): 输出CSV文件路径
            params (Optional[Union[tuple, dict]], optional): 查询参数
            sep (str, optional): CSV分隔符，默认为','
            encoding (str, optional): 文件编码，默认为'utf-8'

        Returns:
            int: 导出的行数

        Example:
            >>> # 导出用户数据
            >>> rows = client.export_to_csv(
            ...     "user_db",
            ...     "SELECT id, name, email FROM users WHERE age > 18",
            ...     "users_export.csv"
            ... )
            >>> print(f"导出了 {rows} 行数据到 users_export.csv")
        """
        try:
            # 执行查询并获取DataFrame
            df = self.query_to_dataframe(db_name, sql, params)
            
            # 导出为CSV
            df.to_csv(output_file, sep=sep, encoding=encoding, index=False)
            
            rows_exported = len(df)
            self._logger.info(f"导出了 {rows_exported} 行数据到 {output_file}")
            return rows_exported
        except Exception as e:
            raise QueryError(f"导出CSV失败: {e}")



    def get_database_metadata(self, db_name: str) -> Dict[str, Any]:
        """
        获取数据库元数据

        Args:
            db_name (str): 目标数据库名称

        Returns:
            Dict[str, Any]: 数据库元数据

        Example:
            >>> metadata = client.get_database_metadata("user_db")
            >>> print(f"数据库引擎: {metadata['engine']}")
            >>> print(f"表数量: {metadata['table_count']}")
        """
        engine = self._get_engine(db_name)
        
        try:
            inspector = engine.inspect()
            tables = inspector.get_table_names()
            
            metadata = {
                'engine': str(engine.url.drivername),
                'database': str(engine.url.database),
                'table_count': len(tables),
                'tables': tables
            }
            
            self._logger.debug(f"获取数据库 {db_name} 的元数据成功")
            return metadata
        except Exception as e:
            raise QueryError(f"获取数据库元数据失败: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出，自动清理资源"""
        self._close_all()
        return False