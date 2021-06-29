"""
Copyright (C) 2021 Clariteia SL

This file is part of minos framework.

Minos framework can not be copied and/or distributed without the express permission of Clariteia SL.
"""
import unittest
from typing import (
    TypedDict,
)

from minos.common import (
    DataTransferObject,
    ModelField,
    ModelType,
)
from tests.model_classes import (
    Bar,
    Foo,
)


class TestDataTransferObject(unittest.IsolatedAsyncioTestCase):
    def test_from_avro_float(self):
        data = {"cost": 3.43}
        schema = [
            {"name": "ShoppingList", "namespace": "", "fields": [{"name": "cost", "type": "float"}], "type": "record"}
        ]

        dto = DataTransferObject.from_avro(schema, data)
        self.assertEqual(3.43, dto.cost)
        self.assertEqual(schema, dto.avro_schema)

    def test_from_avro_list(self):
        data = {"tickets": [3234, 3235, 3236]}
        schema = [
            {
                "fields": [{"name": "tickets", "type": {"items": "int", "type": "array"}}],
                "name": "ShoppingList",
                "namespace": "",
                "type": "record",
            }
        ]
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(data["tickets"], dto.tickets)
        self.assertEqual(schema, dto.avro_schema)

    def test_from_avro_dict(self):
        data = {"tickets": {"a": 1, "b": 2}}
        schema = [
            {
                "fields": [{"name": "tickets", "type": {"type": "map", "values": "int"}}],
                "name": "Order",
                "namespace": "",
                "type": "record",
            }
        ]
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(data["tickets"], dto.tickets)
        self.assertEqual(schema, dto.avro_schema)

    def test_from_avro_int(self):
        data = {"price": 120}
        schema = [{"fields": [{"name": "price", "type": "int"}], "name": "Order", "namespace": "", "type": "record"}]
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(data["price"], dto.price)

        self.assertEqual(schema, dto.avro_schema)

    def test_from_avro_union(self):
        data = {"username": "test"}
        schema = [
            {
                "fields": [{"name": "username", "type": ["string", "null"]}],
                "name": "Order",
                "namespace": "",
                "type": "record",
            }
        ]
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(data["username"], dto.username)
        self.assertEqual(schema, dto.avro_schema)

    def test_from_avro_dto(self):
        expected = DataTransferObject(
            "Order",
            {
                "price": ModelField("price", int, 34),
                "user": ModelField(
                    "user",
                    ModelType.build("User", {"username": list[int]}),
                    DataTransferObject("User", {"username": ModelField("username", list[int], [434324, 66464, 45432])}),
                ),
            },
        )

        data = {"price": 34, "user": {"username": [434324, 66464, 45432]}}
        schema = {
            "fields": [
                {
                    "name": "user",
                    "type": {
                        "fields": [{"name": "username", "type": {"type": "array", "items": "int"}}],
                        "name": "User",
                        "namespace": "",
                        "type": "record",
                    },
                },
                {"name": "price", "type": "int"},
            ],
            "name": "Order",
            "namespace": "",
            "type": "record",
        }
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(expected, dto)

    def test_from_avro_model(self):
        expected = Bar(first=Foo("one"), second=Foo("two"))
        dto = DataTransferObject.from_avro_bytes(expected.avro_bytes)
        self.assertEqual(expected, dto)

    def test_from_avro_with_namespace(self):
        schema = [
            {"fields": [{"name": "price", "type": "int"}], "name": "Order", "namespace": "example", "type": "record"}
        ]
        dto = DataTransferObject.from_avro(schema, {"price": 120})
        self.assertEqual(schema, dto.avro_schema)

    def test_classname(self):
        dto = DataTransferObject("Order", {}, namespace="example")
        self.assertEqual("example.Order", dto.classname)

    def test_constructor_raises(self):
        with self.assertRaises(ValueError):
            DataTransferObject("example.Order", {})

    def test_from_typed_dict_model(self):
        dto = DataTransferObject.from_typed_dict(TypedDict("Foo", {"text": str}), {"text": "test"})
        self.assertEqual(DataTransferObject("Foo", {ModelField("text", str, "test")}), dto)

    def test_from_model_type_model(self):
        dto = DataTransferObject.from_model_type(ModelType.build("Foo", {"text": str}), {"text": "test"})
        self.assertEqual(DataTransferObject("Foo", {ModelField("text", str, "test")}), dto)

    def test_avro_schema(self):
        data = {"price": 34, "user": {"username": [434324, 66464, 45432]}}
        schema = [
            {
                "fields": [
                    {
                        "name": "user",
                        "type": {
                            "fields": [{"name": "username", "type": {"type": "array", "items": "int"}}],
                            "name": "User",
                            "namespace": "",
                            "type": "record",
                        },
                    },
                    {"name": "price", "type": "int"},
                ],
                "name": "Order",
                "namespace": "",
                "type": "record",
            }
        ]
        dto = DataTransferObject.from_avro(schema, data)

        self.assertEqual(schema, dto.avro_schema)

    def test_repr(self):
        dto = DataTransferObject.from_avro(
            [
                {
                    "name": "ShoppingList",
                    "namespace": "lalala",
                    "fields": [{"name": "cost", "type": "float"}],
                    "type": "record",
                }
            ],
            {"cost": 3.43},
        )
        expected = (
            "lalala.ShoppingList[DTO](fields=[ModelField(name='cost', type=<class 'float'>, "
            "value=3.43, parser=None, validator=None)])"
        )
        self.assertEqual(expected, repr(dto))

    def test_str(self):
        dto = DataTransferObject.from_avro(
            [
                {
                    "name": "ShoppingList",
                    "namespace": "",
                    "fields": [{"name": "cost", "type": "float"}],
                    "type": "record",
                }
            ],
            {"cost": 3.43},
        )
        self.assertEqual("ShoppingList[DTO](cost=3.43)", str(dto))


if __name__ == "__main__":
    unittest.main()
