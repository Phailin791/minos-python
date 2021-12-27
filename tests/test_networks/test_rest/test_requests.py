import unittest
import warnings
from uuid import (
    uuid4,
)

from minos.common import (
    ModelType,
    classname,
)
from minos.networks import (
    NotHasContentException,
    NotHasParamsException,
    RestRequest,
    RestResponse,
)
from tests.test_networks.test_rest.utils import (
    avro_mocked_request,
    bytes_mocked_request,
    form_mocked_request,
    json_mocked_request,
    mocked_request,
    text_mocked_request,
)
from tests.utils import (
    FakeModel,
)


class TestRestRequest(unittest.IsolatedAsyncioTestCase):
    def test_raw(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(raw, request.raw)

    def test_raw_request(self):
        raw = mocked_request()
        request = RestRequest(raw)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            # noinspection PyDeprecation
            self.assertEqual(request.raw, request.raw_request)

    def test_repr(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(f"RestRequest({raw!r})", repr(request))

    def test_eq_true(self):
        request = mocked_request()
        self.assertEqual(RestRequest(request), RestRequest(request))

    def test_eq_false(self):
        self.assertNotEqual(RestRequest(mocked_request()), RestRequest(mocked_request()))

    def test_headers(self):
        raw = mocked_request(headers={"something": "123"})
        request = RestRequest(raw)
        self.assertEqual({"something": "123"}, request.headers)

    def test_user(self):
        uuid = uuid4()
        raw = mocked_request(user=uuid)
        request = RestRequest(raw)
        user = request.user
        self.assertEqual(uuid, user)

    def test_user_unset(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(None, request.user)


class TestRestRequestContent(unittest.IsolatedAsyncioTestCase):
    def test_has_content_false(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(False, request.has_content)

    def test_has_content_true(self):
        raw = json_mocked_request(123)
        request = RestRequest(raw)
        self.assertEqual(True, request.has_content)

    async def test_empty_raises(self):
        raw = mocked_request()
        request = RestRequest(raw)
        with self.assertRaises(NotHasContentException):
            await request.content()

    async def test_json_int(self):
        expected = 56

        raw = json_mocked_request(56)
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_json_list(self):
        expected = [{"doors": 3, "color": "blue", "owner": None}, {"doors": 5, "color": "red", "owner": None}]

        raw = json_mocked_request(
            [{"doors": 3, "color": "blue", "owner": None}, {"doors": 5, "color": "red", "owner": None}]
        )
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_json_dict(self):
        expected = {"doors": 3, "color": "blue", "owner": None}

        raw = json_mocked_request({"doors": 3, "color": "blue", "owner": None})
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_form(self):
        expected = {"foo": "foo1", "bar": ["bar1", "bar2"]}

        raw = form_mocked_request({"foo": "foo1", "bar": ["bar1", "bar2"]})
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_avro_int(self):
        expected = 56

        raw = avro_mocked_request(56, "int")
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_avro_uuid(self):
        expected = uuid4()

        raw = avro_mocked_request(expected, {"type": "string", "logicalType": "uuid"})
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_avro_dto(self):
        expected = ModelType.build("FakeModel", {"text": str})("foobar")

        raw = avro_mocked_request(
            {"text": "foobar"}, {"name": "FakeModel", "type": "record", "fields": [{"name": "text", "type": "string"}]}
        )
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_avro_model(self):
        expected = FakeModel("foobar")

        raw = avro_mocked_request(expected.avro_data, expected.avro_schema)
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_text(self):
        expected = "foobar"

        raw = text_mocked_request("foobar")
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_bytes(self):
        expected = bytes("foobar", "utf-8")

        raw = bytes_mocked_request(bytes("foobar", "utf-8"))
        request = RestRequest(raw)
        observed = await request.content()

        self.assertEqual(expected, observed)

    async def test_raises(self):
        raw = mocked_request(content_type="foo/bar", data="foobar".encode())
        request = RestRequest(raw)
        with self.assertRaises(ValueError):
            await request.content()

    async def test_with_type(self):
        # noinspection PyPep8Naming
        Car = ModelType.build("Car", {"doors": int, "color": str, "owner": type(None)})
        expected = [Car(3, "blue", None), Car(5, "red", None)]

        raw = json_mocked_request([{"doors": "3", "color": "blue"}, {"doors": "5", "color": "red"}])
        request = RestRequest(raw)
        observed = await request.content(type_=list[Car])

        self.assertEqual(expected, observed)

    async def test_with_type_classname(self):
        expected = 3

        raw = json_mocked_request("3")
        request = RestRequest(raw)
        observed = await request.content(type_=classname(int))

        self.assertEqual(expected, observed)

    async def test_with_model_type(self):
        expected = 3

        raw = json_mocked_request("3")
        request = RestRequest(raw)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            observed = await request.content(model_type=classname(int))

        self.assertEqual(expected, observed)


class TestRestRequestParams(unittest.IsolatedAsyncioTestCase):
    def test_has_url_params_false(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(False, request.has_url_params)

    def test_has_url_params_true(self):
        raw = mocked_request(url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")])
        request = RestRequest(raw)
        self.assertEqual(True, request.has_url_params)

    async def test_url_params(self):
        expected = {"bar": "2", "foo": ["1", "3"]}

        raw = mocked_request(url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")])
        request = RestRequest(raw)
        observed = await request.url_params()

        self.assertEqual(expected, observed)

    async def test_url_params_with_type(self):
        # noinspection PyPep8Naming
        Params = ModelType.build("Params", {"foo": list[int], "bar": int})
        expected = Params(foo=[1, 3], bar=2)

        raw = mocked_request(url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")])
        request = RestRequest(raw)
        observed = await request.url_params(type_=Params)

        self.assertEqual(expected, observed)

    async def test_url_params_raises(self):
        raw = mocked_request()
        request = RestRequest(raw)
        with self.assertRaises(NotHasParamsException):
            await request.url_params()

    def test_has_query_params_false(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(False, request.has_query_params)

    def test_has_query_params_true(self):
        raw = mocked_request(query_params=[("one", "1"), ("two", "2"), ("one", "3")])
        request = RestRequest(raw)
        self.assertEqual(True, request.has_query_params)

    async def test_query_params(self):
        expected = {"one": ["1", "3"], "two": "2"}

        raw = mocked_request(query_params=[("one", "1"), ("two", "2"), ("one", "3")])
        request = RestRequest(raw)
        observed = await request.query_params()

        self.assertEqual(expected, observed)

    async def test_query_params_with_type(self):
        # noinspection PyPep8Naming
        Params = ModelType.build("Params", {"one": list[int], "two": int})
        expected = Params(one=[1, 3], two=2)

        raw = mocked_request(query_params=[("one", "1"), ("two", "2"), ("one", "3")])
        request = RestRequest(raw)
        observed = await request.query_params(type_=Params)

        self.assertEqual(expected, observed)

    async def test_query_params_raises(self):
        raw = mocked_request()
        request = RestRequest(raw)
        with self.assertRaises(NotHasParamsException):
            await request.query_params()

    def test_has_params_false(self):
        raw = mocked_request()
        request = RestRequest(raw)
        self.assertEqual(False, request.has_params)

    def test_has_params_true(self):
        raw = mocked_request(url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")])
        request = RestRequest(raw)
        self.assertEqual(True, request.has_params)

        raw = mocked_request(query_params=[("one", "1"), ("two", "2"), ("one", "3")])
        request = RestRequest(raw)
        self.assertEqual(True, request.has_params)

        raw = mocked_request(
            url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")],
            query_params=[("one", "1"), ("two", "2"), ("one", "3")],
        )
        request = RestRequest(raw)
        self.assertEqual(True, request.has_params)

    async def test_params(self):
        expected = {"bar": "2", "foo": ["1", "3"], "one": ["1", "3"], "two": "2"}

        raw = mocked_request(
            url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")],
            query_params=[("one", "1"), ("two", "2"), ("one", "3")],
        )
        request = RestRequest(raw)
        observed = await request.params()

        self.assertEqual(expected, observed)

    async def test_params_with_type(self):
        # noinspection PyPep8Naming
        Params = ModelType.build("Params", {"foo": list[int], "bar": int, "one": list[int], "two": int})
        expected = Params(foo=[1, 3], bar=2, one=[1, 3], two=2)

        raw = mocked_request(
            url_params=[("foo", "1"), ("bar", "2"), ("foo", "3")],
            query_params=[("one", "1"), ("two", "2"), ("one", "3")],
        )
        request = RestRequest(raw)
        observed = await request.params(type_=Params)

        self.assertEqual(expected, observed)

    async def test_params_raises(self):
        raw = mocked_request()
        request = RestRequest(raw)
        with self.assertRaises(NotHasParamsException):
            await request.params()


class TestRestResponse(unittest.IsolatedAsyncioTestCase):
    # noinspection PyMissingOrEmptyDocstring
    def setUp(self) -> None:
        self.models = [FakeModel("foo"), FakeModel("bar")]

    async def test_content(self):
        response = RestResponse(self.models)
        self.assertEqual([item.avro_data for item in self.models], await response.raw_content())

    async def test_content_single(self):
        response = RestResponse(self.models[0])
        self.assertEqual(self.models[0].avro_data, await response.raw_content())


if __name__ == "__main__":
    unittest.main()
