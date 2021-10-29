import unittest
from unittest.mock import (
    AsyncMock,
    MagicMock,
    PropertyMock,
    call,
    patch,
)
from uuid import (
    UUID,
    uuid4,
)

from minos.common import (
    TRANSACTION_CONTEXT_VAR,
    Action,
    EventRepositoryEntry,
    MinosRepositoryConflictException,
    Transaction,
    TransactionStatus,
)
from tests.utils import (
    FakeAsyncIterator,
    MinosTestCase,
)


class TestTransaction(MinosTestCase):
    def test_constructor(self):
        transaction = Transaction()

        self.assertIsInstance(transaction.uuid, UUID)
        self.assertEqual(TransactionStatus.PENDING, transaction.status)
        self.assertEqual(None, transaction.event_offset)
        self.assertEqual(True, transaction.autocommit)

        self.assertEqual(self.event_repository, transaction._event_repository)
        self.assertEqual(self.transaction_repository, transaction._transaction_repository)

    def test_constructor_extended(self):
        uuid = uuid4()
        status = TransactionStatus.PENDING
        event_offset = 56
        transaction = Transaction(uuid, status, event_offset, autocommit=False)
        self.assertEqual(uuid, transaction.uuid)
        self.assertEqual(status, transaction.status)
        self.assertEqual(event_offset, transaction.event_offset)
        self.assertEqual(False, transaction.autocommit)

        self.assertEqual(self.event_repository, transaction._event_repository)
        self.assertEqual(self.transaction_repository, transaction._transaction_repository)

    def test_constructor_raw_status(self):
        transaction = Transaction(status="pending")
        self.assertEqual(TransactionStatus.PENDING, transaction.status)

    async def test_async_context_manager_with_context_var(self):
        self.assertEqual(TRANSACTION_CONTEXT_VAR.get(), None)

        async with Transaction() as transaction:
            self.assertEqual(TRANSACTION_CONTEXT_VAR.get(), transaction)

        self.assertEqual(TRANSACTION_CONTEXT_VAR.get(), None)

    async def test_async_context_manager(self):
        with patch("minos.common.Transaction.save") as save_mock, patch(
            "minos.common.Transaction.commit"
        ) as commit_mock:
            async with Transaction():
                self.assertEqual(1, save_mock.call_count)
                self.assertEqual(0, commit_mock.call_count)

            self.assertEqual(1, commit_mock.call_count)

    async def test_async_context_manager_without_autocommit(self):
        with patch("minos.common.Transaction.commit") as commit_mock:
            async with Transaction(autocommit=False) as transaction:
                self.assertEqual(0, commit_mock.call_count)
                transaction.status = TransactionStatus.PENDING

            self.assertEqual(0, commit_mock.call_count)

    async def test_async_context_manager_raises(self):
        with self.assertRaises(ValueError):
            async with Transaction(status=TransactionStatus.COMMITTED):
                pass

        with self.assertRaises(ValueError):
            async with Transaction(status=TransactionStatus.RESERVED):
                pass

        with self.assertRaises(ValueError):
            async with Transaction(status=TransactionStatus.REJECTED):
                pass

        TRANSACTION_CONTEXT_VAR.set(Transaction())
        with self.assertRaises(ValueError):
            async with Transaction():
                pass

    async def test_reserve_success(self) -> None:
        uuid = uuid4()
        validate_mock = AsyncMock(return_value=True)
        save_mock = AsyncMock()

        transaction = Transaction(uuid, TransactionStatus.PENDING)
        transaction.validate = validate_mock
        transaction.save = save_mock

        with patch(
            "minos.common.EventRepository.offset", new_callable=PropertyMock, side_effect=AsyncMock(return_value=55)
        ):
            await transaction.reserve()

        self.assertEqual(1, validate_mock.call_count)
        self.assertEqual(call(), validate_mock.call_args)

        self.assertEqual(
            [call(status=TransactionStatus.RESERVING), call(event_offset=56, status=TransactionStatus.RESERVED)],
            save_mock.call_args_list,
        )

    async def test_reserve_failure(self) -> None:
        uuid = uuid4()
        validate_mock = AsyncMock(return_value=False)
        save_mock = AsyncMock()
        transaction = Transaction(uuid, TransactionStatus.PENDING)
        transaction.validate = validate_mock
        transaction.save = save_mock

        with patch(
            "minos.common.EventRepository.offset", new_callable=PropertyMock, side_effect=AsyncMock(return_value=55)
        ):
            with self.assertRaises(MinosRepositoryConflictException):
                await transaction.reserve()

        self.assertEqual(1, validate_mock.call_count)
        self.assertEqual(call(), validate_mock.call_args)

        self.assertEqual(
            [call(status=TransactionStatus.RESERVING), call(event_offset=56, status=TransactionStatus.REJECTED)],
            save_mock.call_args_list,
        )

    async def test_reserve_raises(self) -> None:
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.RESERVED).reserve()
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.COMMITTED).reserve()
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.REJECTED).reserve()

    async def test_validate_true(self):
        uuid = uuid4()
        another = uuid4()

        agg_uuid = uuid4()

        select_event_1 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 3, bytes(), 2, Action.UPDATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 2, bytes(), 3, Action.UPDATE, transaction_uuid=uuid),
        ]

        select_event_2 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=another),
        ]

        transaction_event_1 = []

        select_event_mock = MagicMock(
            side_effect=[FakeAsyncIterator(select_event_1), FakeAsyncIterator(select_event_2)]
        )
        select_transaction_mock = MagicMock(return_value=FakeAsyncIterator(transaction_event_1))

        self.event_repository.select = select_event_mock
        self.transaction_repository.select = select_transaction_mock

        transaction = Transaction(uuid)

        self.assertTrue(await transaction.validate())

        self.assertEqual(
            [call(transaction_uuid=uuid), call(aggregate_uuid=agg_uuid, version=3)], select_event_mock.call_args_list
        )
        self.assertEqual(
            [
                call(
                    uuid_in=(another,),
                    status_in=(
                        TransactionStatus.RESERVING,
                        TransactionStatus.RESERVED,
                        TransactionStatus.COMMITTING,
                        TransactionStatus.COMMITTED,
                    ),
                )
            ],
            select_transaction_mock.call_args_list,
        )

    async def test_validate_false_already_committed(self):
        uuid = uuid4()

        agg_uuid = uuid4()

        select_event_1 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 3, bytes(), 2, Action.UPDATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 2, bytes(), 3, Action.UPDATE, transaction_uuid=uuid),
        ]

        select_event_2 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE),
        ]

        select_transaction_1 = []

        select_event_mock = MagicMock(
            side_effect=[FakeAsyncIterator(select_event_1), FakeAsyncIterator(select_event_2)]
        )
        select_transaction_mock = MagicMock(return_value=FakeAsyncIterator(select_transaction_1))

        self.event_repository.select = select_event_mock
        self.transaction_repository.select = select_transaction_mock

        transaction = Transaction(uuid)

        self.assertFalse(await transaction.validate())

        self.assertEqual(
            [call(transaction_uuid=uuid), call(aggregate_uuid=agg_uuid, version=3)], select_event_mock.call_args_list
        )
        self.assertEqual(
            [], select_transaction_mock.call_args_list,
        )

    async def test_validate_false_already_reserved(self):
        uuid = uuid4()
        another = uuid4()

        agg_uuid = uuid4()

        select_event_1 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 3, bytes(), 2, Action.UPDATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 2, bytes(), 3, Action.UPDATE, transaction_uuid=uuid),
        ]

        select_event_2 = [
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid),
            EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=another),
        ]

        transaction_event_1 = [Transaction(another, TransactionStatus.RESERVED)]

        select_event_mock = MagicMock(
            side_effect=[FakeAsyncIterator(select_event_1), FakeAsyncIterator(select_event_2)]
        )
        select_transaction_mock = MagicMock(return_value=FakeAsyncIterator(transaction_event_1))

        self.event_repository.select = select_event_mock
        self.transaction_repository.select = select_transaction_mock

        transaction = Transaction(uuid)

        self.assertFalse(await transaction.validate())

        self.assertEqual(
            [call(transaction_uuid=uuid), call(aggregate_uuid=agg_uuid, version=3)], select_event_mock.call_args_list
        )
        self.assertEqual(
            [
                call(
                    uuid_in=(another,),
                    status_in=(
                        TransactionStatus.RESERVING,
                        TransactionStatus.RESERVED,
                        TransactionStatus.COMMITTING,
                        TransactionStatus.COMMITTED,
                    ),
                )
            ],
            select_transaction_mock.call_args_list,
        )

    async def test_reject(self) -> None:
        uuid = uuid4()
        save_mock = AsyncMock()

        transaction = Transaction(uuid, TransactionStatus.RESERVED)
        transaction.save = save_mock

        with patch(
            "minos.common.EventRepository.offset", new_callable=PropertyMock, side_effect=AsyncMock(return_value=55)
        ):
            await transaction.reject()

        self.assertEqual(1, save_mock.call_count)
        self.assertEqual(call(event_offset=56, status=TransactionStatus.REJECTED), save_mock.call_args)

    async def test_reject_raises(self) -> None:
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.COMMITTED).reject()
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.REJECTED).reject()

    async def test_commit(self) -> None:
        uuid = uuid4()

        agg_uuid = uuid4()

        async def _fn(*args, **kwargs):
            yield EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), 1, Action.CREATE, transaction_uuid=uuid)
            yield EventRepositoryEntry(agg_uuid, "c.Car", 3, bytes(), 2, Action.UPDATE, transaction_uuid=uuid)
            yield EventRepositoryEntry(agg_uuid, "c.Car", 2, bytes(), 3, Action.UPDATE, transaction_uuid=uuid)

        select_mock = MagicMock(side_effect=_fn)
        submit_mock = AsyncMock()
        save_mock = AsyncMock()

        self.event_repository.select = select_mock
        self.event_repository.submit = submit_mock

        transaction = Transaction(uuid, TransactionStatus.RESERVED)
        transaction.save = save_mock

        with patch(
            "minos.common.EventRepository.offset", new_callable=PropertyMock, side_effect=AsyncMock(return_value=55)
        ):
            await transaction.commit()

        self.assertEqual(
            [
                call(
                    EventRepositoryEntry(agg_uuid, "c.Car", 1, bytes(), action=Action.CREATE), transaction_uuid_ne=uuid
                ),
                call(
                    EventRepositoryEntry(agg_uuid, "c.Car", 3, bytes(), action=Action.UPDATE), transaction_uuid_ne=uuid
                ),
                call(
                    EventRepositoryEntry(agg_uuid, "c.Car", 2, bytes(), action=Action.UPDATE), transaction_uuid_ne=uuid
                ),
            ],
            submit_mock.call_args_list,
        )

        self.assertEqual(
            [call(status=TransactionStatus.COMMITTING), call(event_offset=56, status=TransactionStatus.COMMITTED)],
            save_mock.call_args_list,
        )

    async def test_commit_pending(self) -> None:
        uuid = uuid4()

        commit_mock = AsyncMock()

        save_mock = AsyncMock()
        transaction = Transaction(uuid, TransactionStatus.PENDING)

        transaction._commit = commit_mock
        transaction.save = save_mock

        async def _fn():
            transaction.status = TransactionStatus.RESERVED

        with patch(
            "minos.common.EventRepository.offset", new_callable=PropertyMock, side_effect=AsyncMock(return_value=55)
        ), patch.object(transaction, "reserve", side_effect=_fn) as reserve_mock:
            await transaction.commit()

        self.assertEqual(1, reserve_mock.call_count)

        self.assertEqual(1, commit_mock.call_count)
        self.assertEqual(call(), commit_mock.call_args)

        self.assertEqual(
            [call(status=TransactionStatus.COMMITTING), call(event_offset=56, status=TransactionStatus.COMMITTED)],
            save_mock.call_args_list,
        )

    async def test_commit_raises(self) -> None:
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.COMMITTED).commit()
        with self.assertRaises(ValueError):
            await Transaction(status=TransactionStatus.REJECTED).commit()

    async def test_save(self) -> None:
        uuid = uuid4()
        submit_mock = AsyncMock()
        self.transaction_repository.submit = submit_mock

        await Transaction(uuid, TransactionStatus.PENDING).save()
        self.assertEqual(1, submit_mock.call_count)
        self.assertEqual(call(Transaction(uuid, TransactionStatus.PENDING)), submit_mock.call_args)

        submit_mock.reset_mock()
        await Transaction(uuid, TransactionStatus.PENDING).save(status=TransactionStatus.COMMITTED)
        self.assertEqual(1, submit_mock.call_count)
        self.assertEqual(call(Transaction(uuid, TransactionStatus.COMMITTED)), submit_mock.call_args)

        submit_mock.reset_mock()
        await Transaction(uuid, TransactionStatus.PENDING).save(event_offset=56)
        self.assertEqual(1, submit_mock.call_count)
        self.assertEqual(call(Transaction(uuid, TransactionStatus.PENDING, 56)), submit_mock.call_args)

    def test_equals(self):
        uuid = uuid4()
        base = Transaction(uuid, TransactionStatus.PENDING, 56)
        self.assertEqual(Transaction(uuid, TransactionStatus.PENDING, 56), base)
        self.assertNotEqual(Transaction(uuid4(), TransactionStatus.PENDING, 56), base)
        self.assertNotEqual(Transaction(uuid, TransactionStatus.COMMITTED, 56), base)
        self.assertNotEqual(Transaction(uuid, TransactionStatus.PENDING, 12), base)

    def test_iter(self):
        uuid = uuid4()
        transaction = Transaction(uuid, TransactionStatus.PENDING, 56)
        self.assertEqual([uuid, TransactionStatus.PENDING, 56], list(transaction))

    def test_repr(self):
        uuid = uuid4()
        transaction = Transaction(uuid, TransactionStatus.PENDING, 56)
        self.assertEqual(
            f"Transaction(uuid={uuid!r}, status={TransactionStatus.PENDING!r}, event_offset={56!r})", repr(transaction)
        )


class TestTransactionStatus(unittest.TestCase):
    def test_value_of_created(self):
        self.assertEqual(TransactionStatus.PENDING, TransactionStatus.value_of("pending"))

    def test_value_of_reserved(self):
        self.assertEqual(TransactionStatus.RESERVED, TransactionStatus.value_of("reserved"))

    def test_value_of_committed(self):
        self.assertEqual(TransactionStatus.COMMITTED, TransactionStatus.value_of("committed"))

    def test_value_of_rejected(self):
        self.assertEqual(TransactionStatus.REJECTED, TransactionStatus.value_of("rejected"))

    def test_value_of_raises(self):
        with self.assertRaises(ValueError):
            TransactionStatus.value_of("foo")


if __name__ == "__main__":
    unittest.main()
