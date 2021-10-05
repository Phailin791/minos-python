import unittest
from shutil import (
    rmtree,
)

from minos.saga import (
    MinosAlreadyOnSagaException,
    MinosSagaAlreadyCommittedException,
    MinosSagaException,
    Saga,
    SagaExecution,
    SagaOperation,
    SagaStep,
    identity_fn,
)
from tests.utils import (
    BASE_PATH,
    commit_callback,
    handle_ticket_success,
    send_create_order,
    send_create_ticket,
    send_delete_order,
    send_delete_ticket,
)


class TestSaga(unittest.TestCase):
    DB_PATH = BASE_PATH / "test_db.lmdb"

    # noinspection PyMissingOrEmptyDocstring
    def tearDown(self) -> None:
        rmtree(self.DB_PATH, ignore_errors=True)

    def test_commit(self):
        saga = Saga()
        observed = saga.commit()
        self.assertEqual(saga, observed)
        self.assertEqual(SagaOperation(identity_fn), saga.commit_operation)

    def test_commit_define_callback(self):
        saga = Saga()
        observed = saga.commit(commit_callback)
        self.assertEqual(saga, observed)
        self.assertEqual(SagaOperation(commit_callback), saga.commit_operation)

    def test_commit_raises(self):
        saga = Saga().commit()
        with self.assertRaises(MinosSagaAlreadyCommittedException):
            saga.commit()

    def test_committed_true(self):
        saga = Saga()
        saga.commit_operation = SagaOperation(identity_fn)
        self.assertTrue(saga.committed)

    def test_committed_false(self):
        saga = Saga()
        self.assertFalse(saga.committed)

    def test_step_raises(self):
        saga = Saga().commit()
        with self.assertRaises(MinosSagaAlreadyCommittedException):
            saga.step()

    def test_empty_step_raises(self):
        with self.assertRaises(MinosSagaException):
            Saga().step().invoke_participant(send_create_order).with_compensation(send_delete_order).step().commit()

    def test_duplicate_operation_raises(self):
        with self.assertRaises(MinosSagaException):
            (
                Saga()
                .step()
                .invoke_participant(send_create_order)
                .with_compensation(send_delete_order)
                .with_compensation(send_delete_ticket)
                .commit()
            )

    def test_missing_send_raises(self):
        with self.assertRaises(MinosSagaException):
            (Saga().step().with_compensation(send_delete_ticket).commit())

    def test_build_execution(self):
        saga = Saga().step().invoke_participant(send_create_order).with_compensation(send_delete_order).commit()
        execution = SagaExecution.from_saga(saga)
        self.assertIsInstance(execution, SagaExecution)

    def test_add_step(self):
        step = SagaStep().invoke_participant(send_create_order)
        saga = Saga().step(step).commit()

        self.assertEqual([step], saga.steps)

    def test_add_step_raises(self):
        step = SagaStep(Saga()).invoke_participant(send_create_order)
        with self.assertRaises(MinosAlreadyOnSagaException):
            Saga().step(step)

    def test_raw(self):
        saga = (
            Saga()
            .step()
            .invoke_participant(send_create_order)
            .with_compensation(send_delete_order)
            .step()
            .invoke_participant(send_create_ticket)
            .on_reply(handle_ticket_success)
            .commit()
        )
        expected = {
            "commit": {"callback": "minos.saga.definitions.operations.identity_fn"},
            "steps": [
                {
                    "invoke_participant": {"callback": "tests.utils.send_create_order"},
                    "on_reply": None,
                    "with_compensation": {"callback": "tests.utils.send_delete_order"},
                },
                {
                    "invoke_participant": {"callback": "tests.utils.send_create_ticket"},
                    "on_reply": {"callback": "tests.utils.handle_ticket_success"},
                    "with_compensation": None,
                },
            ],
        }
        self.assertEqual(expected, saga.raw)

    def test_from_raw(self):
        raw = {
            "commit": {"callback": "minos.saga.definitions.operations.identity_fn"},
            "steps": [
                {
                    "invoke_participant": {"callback": "tests.utils.send_create_order"},
                    "on_reply": None,
                    "with_compensation": {"callback": "tests.utils.send_delete_order"},
                },
                {
                    "invoke_participant": {"callback": "tests.utils.send_create_ticket"},
                    "on_reply": {"callback": "tests.utils.handle_ticket_success"},
                    "with_compensation": None,
                },
            ],
        }
        expected = (
            Saga()
            .step()
            .invoke_participant(send_create_order)
            .with_compensation(send_delete_order)
            .step()
            .invoke_participant(send_create_ticket)
            .on_reply(handle_ticket_success)
            .commit()
        )
        self.assertEqual(expected, Saga.from_raw(raw))

    def test_from_raw_already(self):
        expected = (
            Saga()
            .step()
            .invoke_participant(send_create_order)
            .with_compensation(send_delete_order)
            .step()
            .invoke_participant(send_create_ticket)
            .on_reply(handle_ticket_success)
            .commit()
        )
        self.assertEqual(expected, Saga.from_raw(expected))


if __name__ == "__main__":
    unittest.main()
