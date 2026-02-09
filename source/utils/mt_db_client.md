# Mt_db_client

轻量级多数据库查询客户端

## 核心功能

- **多数据库支持**：支持连接MySQL、PostgreSQL、SQLite等多种类型的数据库
- **连接池管理**：优化连接管理，提高性能，支持连接预热和自动重连
- **查询功能**：支持执行SQL查询语句，支持参数化查询防止SQL注入
- **查询结果缓存**：支持缓存查询结果，提高重复查询性能
- **数据导出**：支持将查询结果导出为CSV文件
- **表结构操作**：支持列出数据库中的表、获取表结构信息
- **DataFrame支持**：支持将查询结果转换为pandas DataFrame，方便数据处理
- **分块读取**：支持分块读取大型数据集，避免内存溢出
- **安全密码管理**：支持从环境变量获取密码，避免硬编码
- **详细的错误处理**：提供详细的错误信息和异常处理
- **上下文管理器**：支持使用with语句自动管理资源

## 使用示例

### 基本查询示例

```python
from coreXAlgo.utils.mt_db_client import MtDBClient

# 配置数据库连接信息
db_configs = {
    "user_db": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "password",
        "database": "user_management"
    }
}

# 创建数据库客户端实例
client = MtDBClient(db_configs, warm_up=True, enable_cache=True)

# 执行查询
result = client.query("user_db", "SELECT * FROM users LIMIT 10")
for row in result:
    print(row)

# 执行带参数的查询
result = client.query("user_db", "SELECT * FROM users WHERE age > :age", {"age": 18})
print(f"年龄大于18的用户数: {len(result)}")
```

### 查询结果转换为DataFrame

```python
# 查询结果转换为DataFrame
df = client.query_to_dataframe("user_db", "SELECT * FROM users")
print(df.head())
print(f"DataFrame形状: {df.shape}")

# 分块读取大型数据集
df_chunks = client.query_to_dataframe("log_db", "SELECT * FROM access_logs", chunk_size=10000)
for chunk in df_chunks:
    print(f"处理分块: {len(chunk)} 行")
    # 处理数据块
```

### 导出数据到CSV

```python
# 导出数据到CSV
rows = client.export_to_csv(
    "user_db",
    "SELECT id, name, email FROM users WHERE age > 18",
    "users_export.csv"
)
print(f"导出了 {rows} 行数据到 users_export.csv")
```

### 表结构操作

```python
# 列出数据库中的表
tables = client.list_tables("user_db")
print(f"数据库中有 {len(tables)} 个表: {tables}")

# 获取表结构
if tables:
    table_name = tables[0]
    schema = client.get_table_schema("user_db", table_name)
    print(f"表 {table_name} 的结构:")
    for column, info in schema.items():
        print(f"- {column}: 类型={info['type']}, 可为空={info['nullable']}")
```

### 使用上下文管理器

```python
# 使用上下文管理器自动管理资源
with MtDBClient(db_configs) as client:
    # 执行查询
    result = client.query("user_db", "SELECT * FROM users LIMIT 5")
    for row in result:
        print(row)
    
    # 无需手动关闭连接，上下文管理器会自动处理
```

### 启用查询缓存

```python
# 启用缓存的查询
result1 = client.query("user_db", "SELECT * FROM users WHERE id = :id", {"id": 1}, use_cache=True)
print("第一次查询结果:", result1)

# 相同查询会使用缓存
result2 = client.query("user_db", "SELECT * FROM users WHERE id = :id", {"id": 1}, use_cache=True)
print("第二次查询结果(使用缓存):", result2)
```

### 从环境变量获取密码

```python
import os

# 设置环境变量
os.environ["DB_PASSWORD"] = "your_secure_password"

# 配置数据库连接信息（使用环境变量获取密码）
db_configs = {
    "user_db": {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password_env": "DB_PASSWORD",  # 从环境变量获取密码
        "database": "user_management"
    }
}

# 创建数据库客户端实例
client = MtDBClient(db_configs)

# 执行查询
result = client.query("user_db", "SELECT * FROM users LIMIT 5")
print(result)
```

## API 参考

```{eval-rst}
.. automodule:: coreXAlgo.utils.mt_db_client
   :members:
   :undoc-members:
   :show-inheritance:
```
