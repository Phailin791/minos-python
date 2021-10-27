import unittest
from typing import (
    Optional,
)

from minos.common import (
    Action,
    AggregateDiff,
    FieldDiff,
    FieldDiffContainer,
    InMemoryRepository,
    InMemorySnapshot,
    ModelRef,
)
from tests.aggregate_classes import (
    Car,
    Owner,
)
from tests.utils import (
    FakeBroker,
    FakeTransactionRepository,
)


class TestAggregate(unittest.IsolatedAsyncioTestCase):
    async def test_create(self):
        async with FakeTransactionRepository() as t, FakeBroker() as b, InMemoryRepository(b, t) as r, InMemorySnapshot(
            r
        ) as s:
            car = await Car.create(doors=3, color="blue", _repository=r, _snapshot=s)
            self.assertEqual(
                [
                    {
                        "data": AggregateDiff(
                            uuid=car.uuid,
                            name=Car.classname,
                            version=1,
                            action=Action.CREATE,
                            created_at=car.created_at,
                            fields_diff=FieldDiffContainer(
                                [
                                    FieldDiff("doors", int, 3),
                                    FieldDiff("color", str, "blue"),
                                    FieldDiff("owner", Optional[list[ModelRef[Owner]]], None),
                                ]
                            ),
                        ),
                        "topic": "CarCreated",
                    }
                ],
                b.calls_kwargs,
            )

    async def test_update(self):
        async with FakeTransactionRepository() as t, FakeBroker() as b, InMemoryRepository(b, t) as r, InMemorySnapshot(
            r
        ) as s:
            car = await Car.create(doors=3, color="blue", _repository=r, _snapshot=s)
            b.reset_mock()

            await car.update(color="red")
            self.assertEqual(
                [
                    {
                        "data": AggregateDiff(
                            uuid=car.uuid,
                            name=Car.classname,
                            version=2,
                            action=Action.UPDATE,
                            created_at=car.updated_at,
                            fields_diff=FieldDiffContainer([FieldDiff("color", str, "red")]),
                        ),
                        "topic": "CarUpdated",
                    },
                    {
                        "data": AggregateDiff(
                            uuid=car.uuid,
                            name=Car.classname,
                            version=2,
                            action=Action.UPDATE,
                            created_at=car.updated_at,
                            fields_diff=FieldDiffContainer([FieldDiff("color", str, "red")]),
                        ),
                        "topic": "CarUpdated.color",
                    },
                ],
                b.calls_kwargs,
            )

    async def test_delete(self):
        async with FakeTransactionRepository() as t, FakeBroker() as b, InMemoryRepository(b, t) as r, InMemorySnapshot(
            r
        ) as s:
            car = await Car.create(doors=3, color="blue", _repository=r, _snapshot=s)
            b.reset_mock()

            await car.delete()
            self.assertEqual(
                [
                    {
                        "data": AggregateDiff(
                            uuid=car.uuid,
                            name=Car.classname,
                            version=2,
                            action=Action.DELETE,
                            created_at=car.updated_at,
                            fields_diff=FieldDiffContainer.empty(),
                        ),
                        "topic": "CarDeleted",
                    }
                ],
                b.calls_kwargs,
            )


if __name__ == "__main__":
    unittest.main()
