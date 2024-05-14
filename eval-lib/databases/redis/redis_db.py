import redis
import time
import uuid
from redis.exceptions import WatchError


class RedisDB():


    def __init__(
        self, host, port,
        password, db,
        max_connections,
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.conn_pool = redis.ConnectionPool(
            host=self.host, port=self.port, max_connections=max_connections,
            password=self.password, db=self.db
        )

    def acquire_lock(self, lockname, acquite_timeout=30, time_out=20):
        """
        :param lockname: Name of the lock
        :param acquire_timeout: Timeout for lock acquisition, default 30 seconds.
        :param lock_timeout: Lock timeout, default 20 seconds
        :return: uuid
        """
        identifier = str(uuid.uuid4())
        end = time.time() + acquite_timeout
        conn = redis.Redis(connection_pool=self.conn_pool)
        while time.time() < end:
            if conn.setnx(lockname, identifier):
                # Set the expiration time of the key and automatically release the lock when it expires
                conn.expire(lockname, time_out)
                return identifier
            # Resetting the expiration time of a lock when it has not been set
            elif conn.ttl(lockname) == -1:
                conn.expire(lockname, time_out)
            time.sleep(0.001)
        return identifier

    def release_lock(self, lockname, identifier):
        """
        :param lockname: Name of the lock
        :param identifier: Lock Identification
        """
        conn = redis.Redis(connection_pool=self.conn_pool)
        with conn.pipeline() as pipe:
            while True:
                try:
                    # If the key is changed by another client, the transaction throws a WatchError exception.
                    pipe.watch(lockname)
                    iden = pipe.get(lockname)
                    if iden and iden.decode('utf-8') == identifier:
                        pipe.multi()
                        pipe.delete(lockname)
                        pipe.execute()
                        return True
                    pipe.unwatch()
                    break
                except WatchError:
                    pass
            return False
