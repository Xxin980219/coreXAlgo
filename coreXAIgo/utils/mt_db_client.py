from typing import Dict, List, Optional, Union
import pymysql
from pymysql.cursors import DictCursor

__all__ = ['MtDBClient']


class MtDBClient:
    """轻量级多数据库查询客户端（仅实现查询功能）"""

    def __init__(self, db_configs: Dict[str, dict]):
        """
        初始化多数据库客户端
        :param db_configs: 数据库配置字典 {db_name: {host,port,user,password,database,...}}
        """
        self._configs = db_configs

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
        if db_name not in self._configs:
            raise ValueError(f"未知数据库: {db_name}")

        conn = pymysql.connect(
            cursorclass=DictCursor,
            autocommit=True,  # 查询专用连接无需事务
            **self._configs[db_name]
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                return cursor.fetchone() if fetchone else cursor.fetchall()
        except pymysql.Error as e:
            raise RuntimeError(f"数据库[{db_name}]查询失败: {e}\nSQL: {sql}")
        finally:
            conn.close()  # 确保连接关闭


# 示例查询
if __name__ == "__main__":
    # 配置多个数据库
    db_configs = {
        "adc_b7_db": {
            "host": "10.141.70.150",
            "port": 3306,
            "user": "root",
            "password": "987654321..",
            "database": "adc-b7-prod"
        }
    }

    sql = """
            SELECT * FROM (
                SELECT 
                -- 	count(*)
                -- 	*
                    t.image_name ,
                    t.image_path ,
                    t.adc_sub_code,
                    t.jpc_sub_code 
                FROM 
                    `adc-b7-prod`.train_dataset_image t
                WHERE 
                     SUBSTRING_INDEX(SUBSTRING_INDEX(t.image_path, '/', 5), '/', -1) in ('BP','bp')
                -- 	 and t.proc_section_code in ('A580A0N')
                -- 	 and SUBSTRING_INDEX(SUBSTRING_INDEX(t.image_path, '/', 9), '/', -1) in ('BF067M4A-T10-7Q00')
                -- 	 and SUBSTR(t.jpc_sub_code , -3, 3) IN ('U4U')
                     and SUBSTR(t.jpc_sub_code , -3, 3) is not null 
                -- group by jpc_sub_code 
            )as filtered
            ORDER BY RAND()
            limit 500;
    """

    # 初始化客户端
    client = MtDBClient(db_configs)
    # 查找BP U3U缺陷的图片
    bp_u3u_img_infos = client.query(
        "adc_b7_db",
        sql,
        fetchone=False
    )
    print(bp_u3u_img_infos)
