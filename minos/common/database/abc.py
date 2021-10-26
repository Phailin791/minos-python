from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Hashable,
    Optional,
)

from aiomisc.pool import (
    ContextManager,
)
from aiopg import (
    Cursor,
)
from dependency_injector.wiring import (
    Provide,
    inject,
)

from ..setup import (
    MinosSetup,
)
from .pool import (
    PostgreSqlPool,
)


class PostgreSqlMinosDatabase(MinosSetup):
    """PostgreSql Minos Database base class."""

    def __init__(self, host: str, port: int, database: str, user: str, password: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

        self._pool = None
        self._owned_pool = False

    async def _destroy(self) -> None:
        if self._owned_pool:
            await self._pool.destroy()
            self._pool = None
            self._owned_pool = False

    async def submit_query_and_fetchone(self, *args, **kwargs) -> tuple:
        """Submit a SQL query and gets the first response.

        :param args: Additional positional arguments.
        :param kwargs: Additional named arguments.
        :return: This method does not return anything.
        """
        return await self.submit_query_and_iter(*args, **kwargs).__anext__()

    # noinspection PyUnusedLocal
    async def submit_query_and_iter(
        self,
        operation: Any,
        parameters: Any = None,
        *,
        timeout: Optional[float] = None,
        lock: Optional[int] = None,
        streaming_mode: bool = False,
        **kwargs,
    ) -> AsyncIterator[tuple]:
        """Submit a SQL query and return an asynchronous iterator.

        :param operation: Query to be executed.
        :param parameters: Parameters to be projected into the query.
        :param timeout: An optional timeout.
        :param lock: Optional key to perform the query with locking. If not set, the query is performed without any
            lock.
        :param streaming_mode: If ``True`` the data fetching is performed in streaming mode, that is iterating over the
            cursor and yielding once a time (requires an opening connection to do that). Otherwise, all the data is
            fetched and keep in memory before yielding it.
        :param kwargs: Additional named arguments.
        :return: This method does not return anything.
        """
        if lock is None:
            context_manager = self.cursor()
        else:
            context_manager = self.lock(lock)

        async with context_manager as cursor:
            await cursor.execute(operation=operation, parameters=parameters, timeout=timeout)

            if streaming_mode:
                async for row in cursor:
                    yield row
                return

            rows = await cursor.fetchall()

        for row in rows:
            yield row

    # noinspection PyUnusedLocal
    async def submit_query(
        self, operation: Any, parameters: Any = None, *, timeout: Optional[float] = None, lock: Any = None, **kwargs,
    ) -> None:
        """Submit a SQL query.

        :param operation: Query to be executed.
        :param parameters: Parameters to be projected into the query.
        :param timeout: An optional timeout.
        :param lock: Optional key to perform the query with locking. If not set, the query is performed without any
            lock.
        :param kwargs: Additional named arguments.
        :return: This method does not return anything.
        """
        if lock is None:
            context_manager = self.cursor()
        else:
            context_manager = self.lock(lock)

        async with context_manager as cursor:
            await cursor.execute(operation=operation, parameters=parameters, timeout=timeout)

    def lock(self, key: Any):
        """TODO"""
        wrapped_cursor = self.pool.cursor()
        return PostgreSqlLock(wrapped_cursor, key)

    def cursor(self, *args, **kwargs) -> AsyncContextManager[Cursor]:
        """Get a connection cursor from the pool.

        :param args: Additional positional arguments.
        :param kwargs: Additional named arguments.
        :return: A ``Cursor`` instance wrapped inside a context manager.
        """
        return self.pool.cursor(*args, **kwargs)

    @property
    def pool(self) -> PostgreSqlPool:
        """Get the connections pool.

        :return: A ``Pool`` object.
        """
        if self._pool is None:
            self._pool, self._owned_pool = self._build_pool()
        return self._pool

    @inject
    def _build_pool(self, pool: PostgreSqlPool = Provide["postgresql_pool"]) -> tuple[PostgreSqlPool, bool]:
        if not isinstance(pool, Provide):
            return pool, False

        pool = PostgreSqlPool(
            host=self.host, port=self.port, database=self.database, user=self.user, password=self.password,
        )
        return pool, True


class PostgreSqlLock(ContextManager):
    """"TODO"""

    def __init__(self, wrapped_cursor: AsyncContextManager[Cursor], key: Any):
        super().__init__(self._fn_enter, self._fn_exit)

        if not isinstance(key, Hashable):
            raise ValueError("TODO")

        if not isinstance(key, int):
            key = hash(key)

        self.wrapped_cursor = wrapped_cursor
        self.key = key

    async def _fn_enter(self):
        cursor = await self.wrapped_cursor.__aenter__()
        await cursor.execute("select pg_advisory_lock(%(key)s)", {"key": self.key})
        return cursor

    async def _fn_exit(self, cursor: Cursor):
        await cursor.execute("select pg_advisory_unlock(%(key)s)", {"key": self.key})
        await self.wrapped_cursor.__aexit__(None, None, None)
