from config import conf
from playhouse.pool import PooledMySQLDatabase

def init_mysql_db(config):
    db = PooledMySQLDatabase(
        database=config.mysql_db,
        host=config.mysql_host,
        port=config.mysql_port,
        user=config.mysql_user,
        password=config.mysql_password,
        max_connections=100,
        charset="utf8",
        stale_timeout=30,
        connect_timeout=20,
    )
    
    # db = MySQLDatabase(
    #     config.mysql_db,
    #     host=config.mysql_host,
    #     port=config.mysql_port,
    #     user=config.mysql_user,
    #     password=config.mysql_password,
    #     charset="utf8",
    # )
    return db


db = init_mysql_db(conf)
