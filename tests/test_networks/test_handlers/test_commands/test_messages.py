"""
Copyright (C) 2021 Clariteia SL

This file is part of minos framework.

Minos framework can not be copied and/or distributed without the express permission of Clariteia SL.
"""
import unittest
from uuid import (
    uuid4,
)

from minos.common import (
    Command,
)
from minos.networks import (
    CommandRequest,
    CommandResponse,
)
from tests.utils import (
    FakeModel,
)


class TestCommandRequest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.models = [FakeModel("foo"), FakeModel("bar")]
        self.saga = uuid4()
        self.command = Command("FooCreated", self.models, self.saga, "AddOrderReply")

    def test_repr(self):
        request = CommandRequest(self.command)
        expected = (
            "CommandRequest(Command(topic=FooCreated, data=[FakeModel(text=foo), FakeModel(text=bar)], "
            f"saga={self.saga!s}, reply_topic=AddOrderReply))"
        )
        self.assertEqual(expected, repr(request))

    def test_eq_true(self):
        self.assertEqual(CommandRequest(self.command), CommandRequest(self.command))

    def test_eq_false(self):
        another = CommandRequest(Command("FooUpdated", self.models, self.saga, "AddOrderReply"))
        self.assertNotEqual(CommandRequest(self.command), another)

    def test_command(self):
        request = CommandRequest(self.command)
        self.assertEqual(self.command, request.command)

    async def test_content(self):
        request = CommandRequest(self.command)
        self.assertEqual(self.models, await request.content())

    async def test_content_single(self):
        request = CommandRequest(Command("FooCreated", self.models[0], self.saga, "AddOrderReply"))
        self.assertEqual(self.models[0], await request.content())


class TestCommandResponse(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.models = [FakeModel("foo"), FakeModel("bar")]

    async def test_content(self):
        response = CommandResponse(self.models)
        self.assertEqual(self.models, await response.content())

    async def test_content_single(self):
        response = CommandResponse(self.models[0])
        self.assertEqual([self.models[0]], await response.content())


if __name__ == "__main__":
    unittest.main()
