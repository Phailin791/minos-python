from __future__ import (
    annotations,
)

from asyncio import (
    gather,
)
from collections import (
    defaultdict,
)
from itertools import (
    chain,
)
from operator import (
    attrgetter,
)
from typing import (
    Any,
    Generic,
    Iterable,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
)
from uuid import (
    UUID,
    SafeUUID,
)

from dependency_injector.wiring import (
    Provide,
    inject,
)

from minos.common import (
    AvroDataEncoder,
    DeclarativeModel,
    Field,
    Model,
    TypeHintBuilder,
    is_model_type,
)
from minos.networks import (
    DynamicBroker,
    DynamicBrokerPool,
)

from ..events import (
    SUBMITTING_EVENT_CONTEXT_VAR,
)
from .entities import (
    Entity,
)

MT = TypeVar("MT")


class AggregateRef(Entity):
    """Aggregate Ref class."""

    version: int

    def __init__(self, uuid: UUID, *args, **kwargs):
        super().__init__(uuid=uuid, *args, **kwargs)


class FieldRef(Field):
    """Ref Field class."""

    @property
    def avro_data(self) -> Any:
        """Compute the avro data of the model.

        If submitting is active then simply the identifier is used, otherwise the complete value is used.

        :return: A dictionary object.
        """
        if not SUBMITTING_EVENT_CONTEXT_VAR.get():
            return super().avro_data

        value = self.value
        if not isinstance(value, UUID):
            value = value.uuid

        return AvroDataEncoder(value).build()


class ModelRef(DeclarativeModel, UUID, Generic[MT]):
    """Model Reference."""

    _field_cls = FieldRef
    data: Union[MT, UUID]

    @inject
    def __init__(
        self, data: Union[MT, UUID], *args, broker_pool: DynamicBrokerPool = Provide["broker_pool"], **kwargs,
    ):
        if not isinstance(data, UUID) and not hasattr(data, "uuid"):
            raise ValueError(f"data must be an {UUID!r} instance or have 'uuid' as one of its fields")
        DeclarativeModel.__init__(self, data, *args, **kwargs)

        self._broker_pool = broker_pool

    def __getattr__(self, item: str) -> Any:
        try:
            return super().__getattr__(item)
        except AttributeError as exc:
            if item != "data":
                return getattr(self.data, item)
            raise exc

    @property
    def int(self) -> int:
        """Get the UUID as a 128-bit integer.

        :return: An integer value.
        """
        return self.uuid.int

    @property
    def is_safe(self) -> SafeUUID:
        """Get an enum indicating whether the UUID has been generated in a way that is safe.

        :return: A ``SafeUUID`` value.
        """
        return self.uuid.is_safe

    def __eq__(self, other):
        return super().__eq__(other) or self.uuid == other or self.data == other

    def __hash__(self):
        return hash(self.uuid)

    @property
    def uuid(self) -> UUID:
        """Get the UUID that identifies the ``Model``.

        :return:
        """
        if not self.resolved:
            return self.data
        return self.data.uuid

    @property
    def data_cls(self) -> Optional[type]:
        """Get data class if available.

        :return: A model type.
        """
        args = get_args(self.type_hints["data"])
        if args:
            return args[0]
        return None

    # noinspection PyUnusedLocal
    async def resolve(self, force: bool = False, **kwargs) -> None:
        """TODO

        :param force: TODO
        :param kwargs: TODO
        :return:
        """
        if not force and self.resolved:
            return

        name = self.data_cls.__name__

        async with self._broker_pool.acquire() as broker:
            await broker.send(data={"uuids": self.uuid}, topic=f"Get{name}")
            self.data = await self._get_response(broker)

    @staticmethod
    async def _get_response(handler: DynamicBroker, **kwargs) -> MT:
        handler_entry = await handler.get_one(**kwargs)
        response = handler_entry.data
        return response.data

    @property
    def resolved(self) -> bool:
        """TODO

        :return: TODO
        """
        return not isinstance(self.data, UUID)


class ModelRefResolver:
    """TODO"""

    # noinspection PyUnusedLocal
    @inject
    def __init__(
        self, broker_pool: DynamicBrokerPool = Provide["broker_pool"], **kwargs,
    ):
        self.broker_pool = broker_pool

    # noinspection PyUnusedLocal
    async def resolve(self, data: Any, **kwargs) -> Any:
        """TODO

        :param data: TODO
        :param kwargs: TODO
        :return: TODO
        """
        missing = ModelRefExtractor(data).build()

        if not len(missing):
            return data

        recovered = await self._query(missing)

        return ModelRefInjector(data, recovered).build()

    async def _query(self, references: dict[str, set[UUID]]) -> dict[UUID, Model]:
        async with self.broker_pool.acquire() as broker:
            futures = (broker.send(data={"uuids": uuids}, topic=f"Get{name}s") for name, uuids in references.items())
            await gather(*futures)

            return {model.uuid: model for model in await self._get_response(broker, len(references))}

    @staticmethod
    async def _get_response(handler: DynamicBroker, count: int, **kwargs) -> Iterable[Model]:
        entries = await handler.get_many(count, **kwargs)
        return chain(*(entry.data.data for entry in entries))


class ModelRefExtractor:
    """Model Reference Extractor class."""

    def __init__(self, value: Any, type_: Optional[type] = None, as_uuids: bool = True):
        if type_ is None:
            type_ = TypeHintBuilder(value).build()
        self.value = value
        self.type_ = type_
        self.as_uuids = as_uuids

    def build(self) -> dict[str, set[UUID]]:
        """Run the model reference extractor.

        :return: A dictionary in which the keys are the class names and the values are the identifiers.
        """
        ans = defaultdict(set)
        self._build(self.value, self.type_, ans)

        if self.as_uuids:
            ans = {k: set(map(attrgetter("uuid"), v)) for k, v in ans.items()}

        return ans

    def _build(self, value: Any, type_: type, ans: dict[str, set[ModelRef]]) -> None:
        if get_origin(type_) is Union:
            type_ = next((t for t in get_args(type_) if get_origin(t) is ModelRef), type_)

        if isinstance(value, (tuple, list, set)):
            self._build_iterable(value, get_args(type_)[0], ans)

        elif isinstance(value, dict):
            self._build_iterable(value.keys(), get_args(type_)[0], ans)
            self._build_iterable(value.values(), get_args(type_)[1], ans)

        elif isinstance(value, ModelRef):
            cls = value.data_cls or get_args(type_)[0]
            name = cls.__name__
            ans[name].add(value)

        elif is_model_type(value):
            # noinspection PyUnresolvedReferences
            for field in value.fields.values():
                self._build(field.value, field.type, ans)

    def _build_iterable(self, value: Iterable, value_: type, ans: dict[str, set[ModelRef]]) -> None:
        for sub_value in value:
            self._build(sub_value, value_, ans)


class ModelRefInjector:
    """Model Reference Injector class."""

    def __init__(self, value: Any, mapper: dict[UUID, Model]):
        self.value = value
        self.mapper = mapper

    def build(self) -> Any:
        """Inject the model instances referenced by identifiers.

        :return: A model in which the model references have been replaced by the values.
        """
        return self._build(self.value)

    def _build(self, value: Any) -> Any:
        if isinstance(value, (tuple, list, set)):
            return type(value)(self._build(v) for v in value)

        if isinstance(value, dict):
            return type(value)((self._build(k), self._build(v)) for k, v in value.items())

        if isinstance(value, UUID) and value in self.mapper:
            return self.mapper[value]

        if is_model_type(value):
            for field in value.fields.values():
                field.value = self._build(field.value)
            return value

        return value
