# Copyright (C) 2020 Clariteia SL
#
# This file is part of minos framework.
#
# Minos framework can not be copied and/or distributed without the express
# permission of Clariteia SL.
from __future__ import (
    annotations,
)

from minos.common import (
    CommandReply,
    MinosConfig,
)

from ..abc import (
    Consumer,
)


class CommandReplyConsumer(Consumer):
    """Command Reply consumer class."""

    TABLE_NAME = "command_reply_queue"

    @classmethod
    def _from_config(cls, *args, config: MinosConfig, **kwargs) -> CommandReplyConsumer:
        topics = [f"{topic}Reply" for topic in config.saga.items]
        return cls(topics=topics, broker=config.saga.broker, **config.saga.queue._asdict(), **kwargs)

    def _is_valid_instance(self, value: bytes) -> bool:
        try:
            CommandReply.from_avro_bytes(value)
            return True
        except:  # noqa E722
            return False
