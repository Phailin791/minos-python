"""
Copyright (C) 2021 Clariteia SL

This file is part of minos framework.

Minos framework can not be copied and/or distributed without the express permission of Clariteia SL.
"""
import unittest
from datetime import (
    date,
    datetime,
    time,
)
from typing import (
    Optional,
    Union,
)
from uuid import (
    UUID,
    uuid4,
)

from minos.common import (
    Field,
    InMemorySnapshot,
    MinosAttributeValidationException,
    MinosMalformedAttributeException,
    MinosReqAttributeException,
    MinosTypeAttributeException,
    ModelRef,
)
from tests.aggregate_classes import (
    Owner,
)
from tests.model_classes import (
    User,
)
from tests.utils import (
    FakeBroker,
    FakeRepository,
)


class TestField(unittest.IsolatedAsyncioTestCase):
    def test_name(self):
        field = Field("test", int, 3)
        self.assertEqual("test", field.name)

    def test_type(self):
        field = Field("test", int, 3)
        self.assertEqual(int, field.type)

    def test_value_int(self):
        field = Field("test", int, 3)
        self.assertEqual(3, field.value)

    def test_value_float(self):
        field = Field("test", float, 3.14)
        self.assertEqual(3.14, field.value)

    def test_value_float_list(self):
        field = Field("test", float, [3.14])
        self.assertEqual(3.14, field.value)

    def test_value_bytes(self):
        field = Field("test", bytes, bytes("foo", "utf-8"))
        self.assertEqual(bytes("foo", "utf-8"), field.value)

    def test_value_date(self):
        value = date(2021, 1, 21)
        field = Field("test", date, value)
        self.assertEqual(value, field.value)

    def test_value_date_int(self):
        field = Field("test", date, 18648)
        self.assertEqual(date(2021, 1, 21), field.value)

    def test_value_date_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", date, "2342342")

    def test_value_time(self):
        value = time(20, 45, 21)
        field = Field("test", time, value)
        self.assertEqual(value, field.value)

    def test_value_time_int(self):
        field = Field("test", time, 74721000000)
        self.assertEqual(time(20, 45, 21), field.value)

    def test_value_time_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", time, "2342342")

    def test_value_datetime(self):
        value = datetime.now()
        field = Field("test", datetime, value)
        self.assertEqual(value, field.value)

    def test_value_datetime_int(self):
        field = Field("test", datetime, 1615584741000000)
        self.assertEqual(datetime(2021, 3, 12, 21, 32, 21), field.value)

    def test_value_datetime_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", datetime, "2342342")

    def test_value_float_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", float, "foo")

    def test_value_bytes_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", bytes, 3)

    def test_value_list_int(self):
        field = Field("test", list[int], [1, 2, 3])
        self.assertEqual([1, 2, 3], field.value)

    def test_value_list_not_list(self):
        field = Field("test", list[int], 3)
        self.assertEqual([3], field.value)

    def test_value_list_str(self):
        field = Field("test", list[str], ["foo", "bar", "foobar"])
        self.assertEqual(["foo", "bar", "foobar"], field.value)

    def test_value_list_model(self):
        field = Field("test", list[User], [User(123), User(456)])
        self.assertEqual([User(123), User(456)], field.value)

    async def test_value_list_model_ref(self):
        async with FakeBroker() as broker, FakeRepository() as repository, InMemorySnapshot() as snapshot:
            field = Field(
                "test",
                list[ModelRef[Owner]],
                [1, 2, Owner("Foo", "Bar", 56, _broker=broker, _repository=repository, _snapshot=snapshot)],
            )
            self.assertEqual(
                [1, 2, Owner("Foo", "Bar", 56, _broker=broker, _repository=repository, _snapshot=snapshot)],
                field.value,
            )

    def test_value_uuid(self):
        value = uuid4()
        field = Field("test", UUID, value)
        self.assertEqual(value, field.value)

    def test_value_uuid_str(self):
        value = uuid4()
        field = Field("test", UUID, str(value))
        self.assertEqual(value, field.value)

    def test_value_uuid_bytes(self):
        value = uuid4()
        field = Field("test", UUID, value.bytes)
        self.assertEqual(value, field.value)

    def test_value_uuid_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", UUID, "foo")
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", UUID, bytes())

    def test_avro_schema_int(self):
        field = Field("test", int, 1)
        expected = {"name": "test", "type": "int"}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_bool(self):
        field = Field("test", bool, True)
        expected = {"name": "test", "type": "boolean"}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_float(self):
        field = Field("test", float, 3.4)
        expected = {"name": "test", "type": "double"}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_string(self):
        field = Field("test", str, "foo")
        expected = {"name": "test", "type": "string"}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_bytes(self):
        field = Field("test", bytes, bytes("foo", "utf-8"))
        expected = {"name": "test", "type": "bytes"}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_date(self):
        field = Field("test", date, date(2021, 1, 21))
        expected = {"name": "test", "type": {"type": "int", "logicalType": "date"}}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_time(self):
        field = Field("test", time, time(20, 32, 12))
        expected = {"name": "test", "type": {"type": "int", "logicalType": "time-micros"}}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_datetime(self):
        field = Field("test", datetime, datetime.now())
        expected = {"name": "test", "type": {"type": "long", "logicalType": "timestamp-micros"}}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_dict(self):
        field = Field("test", dict[str, int], {"foo": 1, "bar": 2})
        expected = {"name": "test", "type": {"type": "map", "values": "int"}}
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_model_ref(self):
        field = Field("test", Optional[ModelRef[Owner]], 1)
        expected = {
            "name": "test",
            "type": [
                {
                    "fields": [
                        {"name": "id", "type": "int"},
                        {"name": "version", "type": "int"},
                        {"name": "name", "type": "string"},
                        {"name": "surname", "type": "string"},
                        {"name": "age", "type": ["int", "null"]},
                    ],
                    "name": "Owner",
                    "namespace": "tests.aggregate_classes.test",
                    "type": "record",
                },
                "int",
                "null",
            ],
        }
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_list_model(self):
        field = Field("test", list[Optional[User]], [User(123), User(456)])
        expected = {
            "name": "test",
            "type": {
                "items": [
                    {
                        "fields": [{"name": "id", "type": "int"}, {"name": "username", "type": ["string", "null"]}],
                        "name": "User",
                        "namespace": "tests.model_classes.test",
                        "type": "record",
                    },
                    "null",
                ],
                "type": "array",
            },
        }
        self.assertEqual(expected, field.avro_schema)

    def test_avro_schema_uuid(self):
        field = Field("test", UUID, uuid4())
        self.assertEqual({"name": "test", "type": {"type": "string", "logicalType": "uuid"}}, field.avro_schema)

    def test_avro_data_float(self):
        field = Field("test", float, 3.14159265359)
        self.assertEqual(3.14159265359, field.avro_data)

    def test_avro_data_list_model(self):
        field = Field("test", list[Optional[User]], [User(123), User(456)])
        expected = [{"id": 123, "username": None}, {"id": 456, "username": None}]
        self.assertEqual(expected, field.avro_data)

    def test_avro_data_dict(self):
        field = Field("test", dict[str, int], {"foo": 1, "bar": 2})
        self.assertEqual({"bar": 2, "foo": 1}, field.avro_data)

    def test_avro_data_bytes(self):
        field = Field("test", bytes, bytes("foo", "utf-8"))
        self.assertEqual(b"foo", field.avro_data)

    def test_avro_data_date(self):
        field = Field("test", date, date(2021, 1, 21))
        self.assertEqual(18648, field.avro_data)

    def test_avro_data_time(self):
        field = Field("test", time, time(20, 45, 21))
        self.assertEqual(74721000000, field.avro_data)

    def test_avro_data_datetime(self):
        value = datetime(2021, 3, 12, 21, 32, 21)
        field = Field("test", datetime, value)
        self.assertEqual(1615584741000000, field.avro_data)

    def test_avro_data_uuid(self):
        value = uuid4()
        field = Field("test", UUID, value)
        self.assertEqual(str(value), field.avro_data)

    def test_value_list_optional(self):
        field = Field("test", list[Optional[int]], [1, None, 3, 4])
        self.assertEqual([1, None, 3, 4], field.value)

    def test_value_list_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", list[int], "hello")

    def test_value_dict(self):
        field = Field("test", dict[str, bool], {"foo": True, "bar": False})
        self.assertEqual({"foo": True, "bar": False}, field.value)

    def test_value_dict_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", dict[str, int], 3)

    def test_dict_keys_raises(self):
        with self.assertRaises(MinosMalformedAttributeException):
            Field("test", dict[int, int], {1: 2, 3: 4})

    def test_value_model(self):
        user = User(1234)
        field = Field("test", User, user)
        self.assertEqual(user, field.value)

    async def test_value_model_ref_value(self):
        async with FakeBroker() as broker, FakeRepository() as repository, InMemorySnapshot() as snapshot:
            user = Owner("Foo", "Bar", _broker=broker, _repository=repository, _snapshot=snapshot)
            field = Field("test", ModelRef[Owner], user)
            self.assertEqual(user, field.value)

    def test_value_model_ref_reference(self):
        field = Field("test", ModelRef[Owner], 1234)
        self.assertEqual(1234, field.value)

    def test_value_model_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", User, "foo")

    def test_value_model_ref_raises(self):
        with self.assertRaises(MinosMalformedAttributeException):
            Field("test", ModelRef[User], User(1234))

    def test_value_model_optional(self):
        field = Field("test", Optional[User], None)
        self.assertIsNone(field.value)

        user = User(1234)
        field.value = user
        self.assertEqual(user, field.value)

    def test_value_unsupported(self):
        with self.assertRaises(MinosTypeAttributeException):
            Field("test", set[int], {3})

    def test_value_setter(self):
        field = Field("test", int, 3)
        field.value = 3
        self.assertEqual(3, field.value)

    def test_value_setter_raises(self):
        field = Field("test", int, 3)
        with self.assertRaises(MinosReqAttributeException):
            field.value = None

    def test_value_setter_list_raises_required(self):
        with self.assertRaises(MinosReqAttributeException):
            Field("test", list[int])

    def test_value_setter_union_raises_required(self):
        with self.assertRaises(MinosReqAttributeException):
            Field("test", Union[int, str])

    def test_value_setter_dict(self):
        field = Field("test", dict[str, bool], {})
        field.value = {"foo": True, "bar": False}
        self.assertEqual({"foo": True, "bar": False}, field.value)

    def test_value_setter_dict_raises(self):
        field = Field("test", dict[str, bool], {})
        with self.assertRaises(MinosTypeAttributeException):
            field.value = "foo"
        with self.assertRaises(MinosTypeAttributeException):
            field.value = {"foo": 1, "bar": 2}
        with self.assertRaises(MinosTypeAttributeException):
            field.value = {1: True, 2: False}

    def test_empty_value_raises(self):
        with self.assertRaises(MinosReqAttributeException):
            Field("id", int)

    def test_union_type(self):
        with self.assertRaises(MinosReqAttributeException):
            Field("test", Union[int, list[int]], None)

    def test_optional_type(self):
        field = Field("test", Optional[int])
        self.assertEqual(Optional[int], field.type)

    def test_empty_optional_value(self):
        field = Field("test", Optional[int])
        self.assertEqual(None, field.value)

    def test_empty_field_equality(self):
        self.assertEqual(Field("test", Optional[int], None), Field("test", Optional[int]))

    def test_value_setter_optional_int(self):
        field = Field("test", Optional[int], 3)
        self.assertEqual(3, field.value)
        field.value = None
        self.assertEqual(None, field.value)
        field.value = 4
        self.assertEqual(4, field.value)

    def test_value_setter_optional_list(self):
        field = Field("test", Optional[list[int]], [1, 2, 3])
        self.assertEqual([1, 2, 3], field.value)
        field.value = None
        self.assertEqual(None, field.value)
        field.value = [4]
        self.assertEqual([4], field.value)

    def test_parser(self):
        field = Field("test", str, "foo", str.title)
        self.assertEqual(str.title, field.parser)

    def test_parser_non_set(self):
        field = Field("test", str, "foo")
        self.assertEqual(None, field.parser)

    def test_parser_value(self):
        field = Field("test", str, "foo", lambda x: x.title())
        self.assertEqual("Foo", field.value)

    def test_parser_with_casting(self):
        field = Field("test", float, "1.234,56", lambda x: x.replace(".", "").replace(",", "."))
        self.assertEqual(1234.56, field.value)

    def test_parser_optional(self):
        field = Field("test", Optional[str], None, lambda x: x if x is None else x.title())
        self.assertEqual(None, field.value)

    def test_validator(self):
        field = Field("test", str, "foo", validator=len)
        self.assertEqual(len, field.validator)

    def test_validator_non_set(self):
        field = Field("test", str, "foo")
        self.assertEqual(None, field.validator)

    def test_validator_ok(self):
        field = Field("test", str, "foo", validator=lambda x: not x.count(" "))
        self.assertEqual("foo", field.value)

    def test_validator_raises(self):
        with self.assertRaises(MinosAttributeValidationException):
            Field("test", str, "foo bar", validator=lambda x: not x.count(" "))

    def test_validator_optional(self):
        field = Field("test", Optional[str], validator=lambda x: not x.count(" "))
        self.assertEqual(None, field.value)

    def test_equal(self):
        self.assertEqual(Field("id", Optional[int], 3), Field("id", Optional[int], 3))
        self.assertNotEqual(Field("id", Optional[int], 3), Field("id", Optional[int], None))
        self.assertNotEqual(Field("id", Optional[int], 3), Field("foo", Optional[int], 3))
        self.assertNotEqual(Field("id", Optional[int], 3), Field("id", int, 3))

    def test_iter(self):
        self.assertEqual(("id", Optional[int], 3, None, None), tuple(Field("id", Optional[int], 3)))

    def test_hash(self):
        self.assertEqual(hash(("id", Optional[int], 3, None, None)), hash(Field("id", Optional[int], 3)))

    def test_repr(self):
        field = Field("test", Optional[int], 1, parser=lambda x: x * 10, validator=lambda x: x > 0)
        self.assertEqual("test=10", repr(field))

    def test_str(self):
        field = Field("test", Optional[int], 1, parser=lambda x: x * 10, validator=lambda x: x > 0)
        self.assertEqual(repr(field), str(field))

    def test_from_avro_int(self):
        obtained = Field.from_avro({"name": "id", "type": "int"}, 1234)
        desired = Field("id", int, 1234)
        self.assertEqual(desired, obtained)

    def test_from_avro_bool(self):
        obtained = Field.from_avro({"name": "id", "type": "boolean"}, True)
        desired = Field("id", bool, True)
        self.assertEqual(desired, obtained)

    def test_from_avro_float(self):
        obtained = Field.from_avro({"name": "id", "type": "float"}, 3.4)
        desired = Field("id", float, 3.4)
        self.assertEqual(desired, obtained)

    def test_from_avro_bytes(self):
        obtained = Field.from_avro({"name": "id", "type": "bytes"}, b"Test")
        desired = Field("id", bytes, b"Test")
        self.assertEqual(desired, obtained)

    def test_from_avro_date(self):
        value = date(2021, 1, 21)
        obtained = Field.from_avro({"name": "id", "type": "int", "logicalType": "date"}, value)
        desired = Field("id", date, value)
        self.assertEqual(desired, obtained)

    def test_from_avro_time(self):
        value = time(20, 45, 21)
        obtained = Field.from_avro({"name": "id", "type": "int", "logicalType": "time-micros"}, value)
        desired = Field("id", time, value)
        self.assertEqual(desired, obtained)

    def test_from_avro_datetime(self):
        value = datetime(2021, 3, 12, 21, 32, 21)
        obtained = Field.from_avro({"name": "id", "type": "long", "logicalType": "timestamp-micros"}, value)
        desired = Field("id", datetime, value)
        self.assertEqual(desired, obtained)

    def test_from_avro_uuid(self):
        uuid = uuid4()
        obtained = Field.from_avro({"name": "id", "type": "string", "logicalType": "uuid"}, uuid)
        desired = Field("id", UUID, uuid)
        self.assertEqual(desired, obtained)

    def test_from_avro_plain_array(self):
        obtained = Field.from_avro({"name": "example", "type": "array", "items": "string"}, ["a", "b", "c"])
        desired = Field("example", list[str], ["a", "b", "c"])
        self.assertEqual(desired, obtained)

    def test_from_avro_plain_map(self):
        obtained = Field.from_avro({"name": "example", "type": "map", "values": "int"}, {"a": 1, "b": 2})
        desired = Field("example", dict[str, int], {"a": 1, "b": 2})
        self.assertEqual(desired, obtained)

    def test_from_avro_nested_arrays(self):
        obtained = Field.from_avro(
            {"name": "example", "type": "array", "items": {"type": {"type": "array", "items": "string"}}},
            [["a", "b", "c"]],
        )
        desired = Field("example", list[list[str]], [["a", "b", "c"]])
        self.assertEqual(desired, obtained)

    def test_from_avro_none(self):
        obtained = Field.from_avro({"name": "example", "type": "null"}, None)
        desired = Field("example", type(None), None)
        self.assertEqual(desired, obtained)

    def test_from_avro_union(self):
        obtained = Field.from_avro({"name": "example", "type": "array", "items": ["int", "string"]}, [1, "a"])
        desired = Field("example", list[Union[int, str]], [1, "a"])
        self.assertEqual(desired, obtained)

    def test_from_avro_raises(self):
        with self.assertRaises(MinosMalformedAttributeException):
            Field.from_avro({"name": "id", "type": "foo"}, None)
        with self.assertRaises(MinosMalformedAttributeException):
            Field.from_avro({"name": "id", "type": "string", "logicalType": "foo"}, None)


if __name__ == "__main__":
    unittest.main()
