"""
Copyright (C) 2021 Clariteia SL

This file is part of minos framework.

Minos framework can not be copied and/or distributed without the express permission of Clariteia SL.
"""

from __future__ import (
    annotations,
)

from asyncio import (
    gather,
)
from typing import (
    NoReturn,
    Type,
    Union,
)

from cached_property import (
    cached_property,
)
from dependency_injector import (
    containers,
    providers,
)

from .configuration import (
    MinosConfig,
)
from .setup import (
    MinosSetup,
)


class DependencyInjector:
    """Async wrapper of ``dependency_injector.containers.Container``. """

    def __init__(self, config: MinosConfig, **kwargs: Union[MinosSetup, Type[MinosSetup]]):
        self.config = config
        self._raw_injections = kwargs

    @cached_property
    def injections(self) -> dict[str, MinosSetup]:
        """TODO

        :return: TODO.
        """

        def _fn(raw: Union[MinosSetup, Type[MinosSetup]]) -> MinosSetup:
            if isinstance(raw, MinosSetup):
                return raw
            return raw.from_config(config=self.config)

        return {key: _fn(value) for key, value in self._raw_injections.items()}

    async def wire(self, *args, **kwargs) -> NoReturn:
        """Connect the configuration.

        :return: This method does not return anything.
        """
        self.container.wire(*args, **kwargs)

        await gather(*(injection.setup() for injection in self.injections.values()))

    async def unwire(self) -> NoReturn:
        """Disconnect the configuration.

        :return: This method does not return anything.
        """
        self.container.unwire()
        await gather(*(injection.destroy() for injection in self.injections.values()))

    @cached_property
    def container(self) -> containers.Container:
        """Get the dependencies container.

        :return: A ``Container`` instance.
        """
        container = containers.DynamicContainer()
        container.config = providers.Object(self.config)

        for name, injection in self.injections.items():
            container.set_provider(name, providers.Object(injection))
        return container

    def __getattr__(self, item: str) -> MinosSetup:
        if item not in self.injections:
            raise AttributeError(f"{type(self).__name__!r} does not contain the {item!r} attribute.")
        return self.injections[item]
