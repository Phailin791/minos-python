"""
Copyright (C) 2021 Clariteia SL

This file is part of minos framework.

Minos framework can not be copied and/or distributed without the express permission of Clariteia SL.
"""
from __future__ import (
    annotations,
)

from itertools import (
    count,
)
from typing import (
    AsyncIterator,
    Optional,
)

from .abc import (
    MinosRepository,
)
from .entries import (
    MinosRepositoryEntry,
)


class MinosInMemoryRepository(MinosRepository):
    """Memory-based implementation of the repository class in ``minos``."""

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._storage = list()
        self._id_generator = count()

    async def _submit(self, entry: MinosRepositoryEntry) -> MinosRepositoryEntry:
        """Store new deletion entry into de repository.

        :param entry: Entry to be stored.
        :return: This method does not return anything.
        """
        if entry.aggregate_id == 0:
            entry.aggregate_id = self._generate_next_aggregate_id(entry.aggregate_name)
        entry.version = self._get_next_version_id(entry.aggregate_name, entry.aggregate_id)
        entry.id = self._generate_next_id()
        self._storage.append(entry)
        return entry

    def _generate_next_id(self) -> int:
        return next(self._id_generator) + 1

    def _generate_next_aggregate_id(self, aggregate_name: str) -> int:
        """Generate a new unique id for the given aggregate name.

        :param aggregate_name: The name of the aggregate.
        :return: A positive-integer value.
        """
        iterable = iter(self._storage)
        iterable = filter(lambda entry: entry.aggregate_name == aggregate_name, iterable)
        return len(list(iterable)) + 1

    def _get_next_version_id(self, aggregate_name: str, aggregate_id: int) -> int:
        """Generate a new version number for the given aggregate name and identifier.

        :param aggregate_name: The name of the aggregate.
        :param aggregate_id: The identifier of the aggregate.
        :return: A positive-integer value.
        """
        iterable = iter(self._storage)
        iterable = filter(
            lambda entry: entry.aggregate_name == aggregate_name and entry.aggregate_id == aggregate_id, iterable,
        )
        return len(list(iterable)) + 1

    async def _select(
        self,
        aggregate_id: Optional[int] = None,
        aggregate_name: Optional[str] = None,
        version: Optional[int] = None,
        version_lt: Optional[int] = None,
        version_gt: Optional[int] = None,
        version_le: Optional[int] = None,
        version_ge: Optional[int] = None,
        id: Optional[int] = None,
        id_lt: Optional[int] = None,
        id_gt: Optional[int] = None,
        id_le: Optional[int] = None,
        id_ge: Optional[int] = None,
        *args,
        **kwargs
    ) -> AsyncIterator[MinosRepositoryEntry]:

        # noinspection DuplicatedCode
        def _fn_filter(entry: MinosRepositoryEntry) -> bool:
            if aggregate_id is not None and aggregate_id != entry.aggregate_id:
                return False
            if aggregate_name is not None and aggregate_name != entry.aggregate_name:
                return False
            if version is not None and version != entry.version:
                return False
            if version_lt is not None and version_lt <= entry.version:
                return False
            if version_gt is not None and version_gt >= entry.version:
                return False
            if version_le is not None and version_le < entry.version:
                return False
            if version_ge is not None and version_ge > entry.version:
                return False
            if id is not None and id != entry.id:
                return False
            if id_lt is not None and id_lt <= entry.id:
                return False
            if id_gt is not None and id_gt >= entry.id:
                return False
            if id_le is not None and id_le < entry.id:
                return False
            if id_ge is not None and id_ge > entry.id:
                return False
            return True

        iterable = iter(self._storage)
        iterable = filter(_fn_filter, iterable)
        for item in iterable:
            yield item
