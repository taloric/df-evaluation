from .redis_db import RedisDB
import redis
from . import const




class RedisRunnerInfo(RedisDB):


    def __init__(
        self, host, port,
        password, db,
        max_connections,
    ) -> None:
        super().__init__(
            host, port,
            password, db,
            max_connections,
        )

    def init_runner_info(self, uuid):
        runner_info = {
            "uuid": uuid,
            "case-control-status": const.CASE_STATUS_RUNNING,
            "runner-status": const.CASE_STATUS_INIT,
            "case-status": const.CASE_STATUS_INIT,
        }
        conn = redis.Redis(connection_pool=self.conn_pool)
        runner_key_name = f"{const.RUNNER_KEY}-{uuid}"
        conn.hmset(runner_key_name, runner_info)
        # runner timeout
        conn.expire(runner_key_name, const.RUNNER_TIMEOUT)
        
    def update_runner_info(self, uuid, info: dict):
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        conn = redis.Redis(connection_pool=self.conn_pool)
        # update = False
        for k, v in info.items():
            if conn.hget(key_name, k) != v:
                conn.hset(key_name, k, v)
                # update = True
        # if update:
        #     updated = int(time.time())
        #     conn.hset(key_name, "updated_time", updated)
        self.release_lock(const.GLOBAL_LOCK, lock)

    def get_runner_info(self, uuid) -> dict:
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        runner_info = {}
        conn = redis.Redis(connection_pool=self.conn_pool)
        hash_all = conn.hgetall(key_name)
        if hash_all:
            for k, v in hash_all.items():
                runner_info[k.decode()] = v.decode()
        self.release_lock(const.GLOBAL_LOCK, lock)
        return runner_info

    def delete_runner_info(self, uuid):
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        conn = redis.Redis(connection_pool=self.conn_pool)
        conn.delete(key_name)
        self.release_lock(const.GLOBAL_LOCK, lock)

    def pause_case(self, uuid):
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        conn = redis.Redis(connection_pool=self.conn_pool)
        conn.hset(key_name, "case-control-status", const.CASE_STATUS_PAUSED)
        self.release_lock(const.GLOBAL_LOCK, lock)
    
    def cancel_case(self, uuid):
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        conn = redis.Redis(connection_pool=self.conn_pool)
        conn.hset(key_name, "case-control-status", const.CASE_STATUS_CANCELLED)
        self.release_lock(const.GLOBAL_LOCK, lock)
    
    def resume_case(self, uuid):
        key_name = f"{const.RUNNER_KEY}-{uuid}"
        lock = self.acquire_lock(const.GLOBAL_LOCK)
        conn = redis.Redis(connection_pool=self.conn_pool)
        conn.hset(key_name, "case-control-status", const.CASE_STATUS_RUNNING)
        self.release_lock(const.GLOBAL_LOCK, lock)