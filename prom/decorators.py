# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import

import time
from functools import wraps
import logging
import gevent
from decorators import classproperty

from .exception import InterfaceError
from .compat import *


logger = logging.getLogger(__name__)


def reconnecting(count=None, backoff=None):
    """this is a very specific decorator meant to be used on Interface classes.
    It will attempt to reconnect if the connection is closed and run the same 
    method again.

    TODO -- I think this will have issues with transactions using passed in
    connections, ie, you pass in a transacting connection to the insert() method
    and that connection gets dropped, this will reconnect but the transaction will
    be hosed.

    count -- integer -- how many attempts to run the method, defaults to 3
    backoff -- float -- how long to sleep on failure, defaults to 1.0
    """
    # we get tricksy here so we can manipulate these values in the wrapped function,
    # this is one of the first times I wish we were on Python 3
    # http://stackoverflow.com/a/9264845/5006
    reconn_params = {
        "count": count,
        "backoff": backoff
    }

    def retry_decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            count = reconn_params["count"]
            backoff = reconn_params["backoff"]

            if count is None:
                count = self.connection_config.options.get('reconnect_attempts', 3)

            if backoff is None:
                backoff = self.connection_config.options.get('reconnect_backoff', 1.0)

            count = int(count)
            backoff = float(backoff)

            for attempt in range(1, count + 1):
                try:
                    backoff_seconds = float(attempt - 1) * backoff
                    if backoff_seconds:
                        logger.debug("sleeping {} seconds before attempt {}".format(
                            backoff_seconds,
                            attempt
                        ))
                        time.sleep(backoff_seconds)

                    return func(self, *args, **kwargs)

                except InterfaceError as e:
                    e_msg = String(e.e)
                    # TODO -- this gets us by SQLite and Postgres, but might not
                    # work in the future, so this needs to be a tad more robust
                    if "closed" in e_msg.lower():
                        if attempt == count:
                            logger.debug("all {} attempts failed".format(count))
                            raise
                        else:
                            logger.debug("attempt {}/{} failed, retrying".format(
                                attempt,
                                count
                            ))

                    else:
                        raise

        return wrapper

    return retry_decorator

