import unittest
from typing import Optional, Union

from minos.common import ModelField, ModelRef, MinosReqAttributeException, MinosTypeAttributeException,MinosReqAttributeException
from tests.modelClasses import User


class TestModelField(unittest.TestCase):

    def test_name(self):
        field = ModelField("test", int, 3)
        self.assertEqual("test", field.name)

    def test_type(self):
        field = ModelField("test", int, 3)
        self.assertEqual(int, field.type)

    def test_value_int(self):
        field = ModelField("test", int, 3)
        self.assertEqual(3, field.value)

    def test_value_float(self):
        field = ModelField("test", float, 3.14)
        self.assertEqual(3.14, field.value)

    def test_value_float_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            ModelField("test", float, [3])
        with self.assertRaises(MinosTypeAttributeException):
            ModelField("test", float, "foo")

    def test_value_list(self):
        field = ModelField("test", list[int], [1, 2, 3])
        self.assertEqual([1, 2, 3], field.value)

    def test_value_list_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            ModelField("test", list[int], 3)

    def test_value_dict(self):
        field = ModelField("test", dict[str, bool], {"foo": True, "bar": False})
        self.assertEqual({"foo": True, "bar": False}, field.value)

    def test_value_dict_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            ModelField("test", dict[str, int], 3)

    def test_value_model_ref(self):
        user = User(1234)
        field = ModelField("test", ModelRef[User], user)
        self.assertEqual(user, field.value)

    def test_value_model_ref_raises(self):
        with self.assertRaises(MinosTypeAttributeException):
            ModelField("test", ModelRef[User], "foo")

    def test_value_model_ref_optional(self):
        field = ModelField("test", Optional[ModelRef[User]], None)
        self.assertIsNone(field.value)

        user = User(1234)
        field.value = user
        self.assertEqual(user, field.value)

    def test_value_setter(self):
        field = ModelField("test", int, 3)
        field.value = 3
        self.assertEqual(3, field.value)

    def test_value_setter_raises(self):
        field = ModelField("test", int, 3)
        with self.assertRaises(MinosReqAttributeException):
            field.value = None

    def test_value_setter_list_raises_required(self):
        with self.assertRaises(MinosReqAttributeException):
            ModelField("test", list[int])

    def test_value_setter_union_raises_required(self):
        with self.assertRaises(MinosReqAttributeException):
            ModelField("test", Union[int, str])

    def test_value_setter_dict(self):
        field = ModelField("test", dict[str, bool], {})
        field.value = {"foo": True, "bar": False}
        self.assertEqual({"foo": True, "bar": False}, field.value)

    def test_value_setter_dict_raises(self):
        field = ModelField("test", dict[str, bool], {})
        with self.assertRaises(MinosTypeAttributeException):
            field.value = "foo"
        with self.assertRaises(MinosTypeAttributeException):
            field.value = {"foo": 1, "bar": 2}
        with self.assertRaises(MinosTypeAttributeException):
            field.value = {1: True, 2: False}

    def test_empty_value_raises(self):
        with self.assertRaises(MinosReqAttributeException):
            ModelField("id", int)

    def test_optional_type(self):
        field = ModelField("test", Optional[int])
        self.assertEqual(Optional[int], field.type)

    def test_empty_optional_value(self):
        field = ModelField("test", Optional[int])
        self.assertEqual(None, field.value)

    def test_empty_field_equality(self):
        self.assertEqual(ModelField("test", Optional[int], None), ModelField("test", Optional[int]))

    def test_value_setter_optional_int(self):
        field = ModelField("test", Optional[int], 3)
        self.assertEqual(3, field.value)
        field.value = None
        self.assertEqual(None, field.value)
        field.value = 4
        self.assertEqual(4, field.value)

    def test_value_setter_optional_list(self):
        field = ModelField("test", Optional[list[int]], [1, 2, 3])
        self.assertEqual([1, 2, 3], field.value)
        field.value = None
        self.assertEqual(None, field.value)
        field.value = [4]
        self.assertEqual([4], field.value)

    def test_parser(self):
        parser = lambda x: x.title()
        field = ModelField("test", str, "foo", parser)
        self.assertEqual(parser, field.parser)

    def test_parser_non_set(self):
        field = ModelField("test", str, "foo")
        self.assertEqual(None, field.parser)

    def test_parser_value(self):
        field = ModelField("test", str, "foo", lambda x: x.title())
        self.assertEqual("Foo", field.value)

    def test_parser_with_casting(self):
        field = ModelField("test", float, "1.234,56", lambda x: x.replace(".", "").replace(",", "."))
        self.assertEqual(1234.56, field.value)

    def test_parser_optional(self):
        field = ModelField("test", Optional[str], None, lambda x: x.title())
        self.assertEqual(None, field.value)

    def test_equal(self):
        self.assertEqual(ModelField("id", Optional[int], 3), ModelField("id", Optional[int], 3))
        self.assertNotEqual(ModelField("id", Optional[int], 3), ModelField("id", Optional[int], None))
        self.assertNotEqual(ModelField("id", Optional[int], 3), ModelField("foo", Optional[int], 3))
        self.assertNotEqual(ModelField("id", Optional[int], 3), ModelField("id", int, 3))

    def test_iter(self):
        self.assertEqual(("id", Optional[int], 3, None), tuple(ModelField("id", Optional[int], 3)))

    def test_hash(self):
        self.assertEqual(hash(("id", Optional[int], 3, None)), hash(ModelField("id", Optional[int], 3)))

    def test_repr(self):
        field = ModelField("test", Optional[int], 1, lambda x: x * 10)
        self.assertEqual("ModelField(name='test', type=typing.Optional[int], value=10, parser=<lambda>)", repr(field))


if __name__ == '__main__':
    unittest.main()
