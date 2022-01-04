import unittest
from unittest.mock import (
    patch,
)
from uuid import (
    uuid4,
)

from minos.common import (
    EmptyMinosModelSequenceException,
    MultiTypeMinosModelSequenceException,
)
from tests.model_classes import (
    Auth,
    Bar,
    Customer,
    Foo,
    FooBar,
    GenericUser,
    ShoppingList,
    User,
)
from tests.utils import (
    MinosTestCase,
)


class TestMinosModelAvro(MinosTestCase):
    def test_avro_schema(self):
        expected = [
            {
                "fields": [
                    {
                        "name": "user",
                        "type": [
                            {
                                "fields": [
                                    {"name": "id", "type": "int"},
                                    {"name": "username", "type": ["string", "null"]},
                                ],
                                "name": "User",
                                "namespace": "tests.model_classes.goodbye",
                                "type": "record",
                            },
                            "null",
                        ],
                    },
                    {"name": "cost", "type": "double"},
                ],
                "name": "ShoppingList",
                "namespace": "tests.model_classes.hello",
                "type": "record",
            }
        ]
        with patch("minos.common.AvroSchemaEncoder._generate_random_str", side_effect=["goodbye", "hello"]):
            self.assertEqual(expected, ShoppingList.avro_schema)

    def test_avro_data(self):
        shopping_list = ShoppingList(User(1234))
        expected = {"cost": float("inf"), "user": {"id": 1234, "username": None}}
        self.assertEqual(expected, shopping_list.avro_data)

    def test_avro_bytes(self):
        shopping_list = ShoppingList(User(1234))
        self.assertIsInstance(shopping_list.avro_bytes, bytes)

    def test_avro_schema_generics(self):
        expected = [
            {
                "fields": [{"name": "username", "type": ["string", "int"]}],
                "name": "GenericUser",
                "namespace": "tests.model_classes.hello",
                "type": "record",
            }
        ]
        with patch("minos.common.AvroSchemaEncoder._generate_random_str", side_effect=["hello"]):
            self.assertEqual(expected, GenericUser.avro_schema)

    def test_avro_schema_generics_nested(self):
        expected = [
            {
                "fields": [
                    {
                        "name": "user",
                        "type": [
                            {
                                "fields": [{"name": "username", "type": "string"}],
                                "name": "GenericUser",
                                "namespace": "tests.model_classes.goodbye",
                                "type": "record",
                            }
                        ],
                    }
                ],
                "name": "Auth",
                "namespace": "tests.model_classes.hello",
                "type": "record",
            }
        ]
        with patch("minos.common.AvroSchemaEncoder._generate_random_str", side_effect=["goodbye", "hello"]):
            self.assertEqual(expected, Auth.avro_schema)

    def test_avro_schema_simple(self):
        customer = Customer(1234)
        expected = [
            {
                "fields": [
                    {"name": "id", "type": "int"},
                    {"name": "username", "type": ["string", "null"]},
                    {"name": "name", "type": ["string", "null"]},
                    {"name": "surname", "type": ["string", "null"]},
                    {"name": "is_admin", "type": ["boolean", "null"]},
                    {"name": "lists", "type": [{"items": "int", "type": "array"}, "null"]},
                ],
                "name": "Customer",
                "namespace": "tests.model_classes.hello",
                "type": "record",
            }
        ]
        with patch("minos.common.AvroSchemaEncoder._generate_random_str", side_effect=["hello"]):
            self.assertEqual(expected, customer.avro_schema)

    def test_avro_data_simple(self):
        customer = Customer(1234)
        expected = {
            "id": 1234,
            "is_admin": None,
            "lists": None,
            "name": None,
            "surname": None,
            "username": None,
        }
        self.assertEqual(expected, customer.avro_data)

    def test_avro_avro_str_single(self):
        customer = Customer(1234)
        avro_str = customer.avro_str
        self.assertIsInstance(avro_str, str)
        decoded_customer = Customer.from_avro_str(avro_str)
        self.assertEqual(customer, decoded_customer)

    def test_avro_bytes_single(self):
        customer = Customer(1234)
        avro_bytes = customer.avro_bytes
        self.assertIsInstance(avro_bytes, bytes)
        decoded_customer = Customer.from_avro_bytes(avro_bytes)
        self.assertEqual(customer, decoded_customer)

    def test_avro_to_avro_str(self):
        customers = [Customer(1234), Customer(5678)]
        avro_str = Customer.to_avro_str(customers)
        self.assertIsInstance(avro_str, str)
        decoded_customer = Customer.from_avro_str(avro_str)
        self.assertEqual(customers, decoded_customer)

    def test_avro_bytes_sequence(self):
        customers = [Customer(1234), Customer(5678)]
        avro_bytes = Customer.to_avro_bytes(customers)
        self.assertIsInstance(avro_bytes, bytes)
        decoded_customer = Customer.from_avro_bytes(avro_bytes)
        self.assertEqual(customers, decoded_customer)

    def test_avro_bytes_composed(self):
        shopping_list = ShoppingList(User(1234), cost="1.234")
        avro_bytes = shopping_list.avro_bytes
        self.assertIsInstance(avro_bytes, bytes)
        decoded_shopping_list = ShoppingList.from_avro_bytes(avro_bytes)
        self.assertEqual(shopping_list, decoded_shopping_list)

    def test_avro_bytes_empty_sequence(self):
        with self.assertRaises(EmptyMinosModelSequenceException):
            Customer.to_avro_bytes([])

    def test_avro_bytes_multi_type_sequence(self):
        with self.assertRaises(MultiTypeMinosModelSequenceException):
            Customer.to_avro_bytes([User(1234), Customer(5678)])

    def test_multiple_fields_avro_schema(self):
        bar = Bar(first=Foo("one"), second=Foo("two"))
        expected = [
            {
                "fields": [
                    {
                        "name": "first",
                        "type": {
                            "fields": [{"name": "text", "type": "string"}],
                            "name": "Foo",
                            "namespace": "tests.model_classes.hello",
                            "type": "record",
                        },
                    },
                    {
                        "name": "second",
                        "type": {
                            "fields": [{"name": "text", "type": "string"}],
                            "name": "Foo",
                            "namespace": "tests.model_classes.goodbye",
                            "type": "record",
                        },
                    },
                ],
                "name": "Bar",
                "namespace": "tests.model_classes.one",
                "type": "record",
            }
        ]

        with patch("minos.common.AvroSchemaEncoder._generate_random_str", side_effect=["hello", "goodbye", "one"]):
            self.assertEqual(expected, bar.avro_schema)

    def test_multiple_fields_avro_data(self):
        bar = Bar(first=Foo("one"), second=Foo("two"))
        expected = {"first": {"text": "one"}, "second": {"text": "two"}}

        self.assertEqual(expected, bar.avro_data)

    def test_multiple_fields_avro_bytes(self):
        original = Bar(first=Foo("one"), second=Foo("two"))
        serialized = original.avro_bytes
        recovered = Bar.from_avro_bytes(serialized)
        self.assertEqual(original, recovered)

    def test_uuid_avro_bytes(self):
        original = FooBar(uuid4())
        serialized = original.avro_bytes
        recovered = FooBar.from_avro_bytes(serialized)
        self.assertEqual(original, recovered)

    def test_avro_bytes_generics(self):
        base = GenericUser("foo")
        self.assertEqual(base, GenericUser.from_avro_bytes(base.avro_bytes))

    def test_avro_bytes_generics_nested(self):
        base = Auth(GenericUser("foo"))
        self.assertEqual(base, Auth.from_avro_bytes(base.avro_bytes))


if __name__ == "__main__":
    unittest.main()
