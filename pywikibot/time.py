"""Time handling module."""
#
# (C) Pywikibot team, 2009-2022
#
# Distributed under the terms of the MIT license.
#
import datetime
import re
from typing import Type, Union

from pywikibot.tools import classproperty

__all__ = ['Timestamp']


class Timestamp(datetime.datetime):

    """Class for handling MediaWiki timestamps.

    This inherits from datetime.datetime, so it can use all of the methods
    and operations of a datetime object. To ensure that the results of any
    operation are also a Timestamp object, be sure to use only Timestamp
    objects (and datetime.timedeltas) in any operation.

    Use Timestamp.fromISOformat() and Timestamp.fromtimestampformat() to
    create Timestamp objects from MediaWiki string formats.
    As these constructors are typically used to create objects using data
    passed provided by site and page methods, some of which return a Timestamp
    when previously they returned a MediaWiki string representation, these
    methods also accept a Timestamp object, in which case they return a clone.

    Alternatively, Timestamp.set_timestamp() can create Timestamp objects from
    Timestamp, datetime.datetime object, or strings compliant with ISO8601,
    MW, or POSIX formats.

    Use Site.server_time() for the current time; this is more reliable
    than using Timestamp.utcnow().
    """

    mediawikiTSFormat = '%Y%m%d%H%M%S'  # noqa: N815
    _ISO8601Format_new = '{0:+05d}-{1:02d}-{2:02d}T{3:02d}:{4:02d}:{5:02d}Z'

    @classmethod
    def set_timestamp(cls: Type['Timestamp'],
                      ts: Union[str, datetime.datetime, 'Timestamp']
                      ) -> 'Timestamp':
        """Set Timestamp from input object.

        ts is converted to a datetime naive object representing UTC time.
        String shall be compliant with:
        - Mediwiki timestamp format: YYYYMMDDHHMMSS
        - ISO8601 format: YYYY-MM-DD[T ]HH:MM:SS[Z|±HH[MM[SS[.ffffff]]]]
        - POSIX format: seconds from Unix epoch S{1,13}[.ffffff]]

        :param ts: Timestamp, datetime.datetime or str
        :return: Timestamp object
        :raises ValuError: conversion failed
        """
        if isinstance(ts, cls):
            return ts
        if isinstance(ts, datetime.datetime):
            return cls._from_datetime(ts)
        if isinstance(ts, str):
            return cls._from_string(ts)

    @staticmethod
    def _from_datetime(dt: datetime.datetime) -> 'Timestamp':
        """Convert a datetime.datetime timestamp to a Timestamp object."""
        return Timestamp(dt.year, dt.month, dt.day, dt.hour,
                         dt.minute, dt.second, dt.microsecond,
                         dt.tzinfo)

    @classmethod
    def _from_mw(cls: Type['Timestamp'], timestr: str) -> 'Timestamp':
        """Convert a string in MW format to a Timestamp object.

        Mediwiki timestamp format: YYYYMMDDHHMMSS
        """
        RE_MW = r'\d{14}$'  # noqa: N806
        m = re.match(RE_MW, timestr)

        if not m:
            msg = "time data '{timestr}' does not match MW format."
            raise ValueError(msg.format(timestr=timestr))

        return cls.strptime(timestr, cls.mediawikiTSFormat)

    @classmethod
    def _from_iso8601(cls: Type['Timestamp'], timestr: str) -> 'Timestamp':
        """Convert a string in ISO8601 format to a Timestamp object.

        ISO8601 format:
        - YYYY-MM-DD[T ]HH:MM:SS[[.,]ffffff][Z|±HH[MM[SS[.ffffff]]]]
        """
        RE_ISO8601 = (r'(?:\d{4}-\d{2}-\d{2})(?P<sep>[T ])'  # noqa: N806
                      r'(?:\d{2}:\d{2}:\d{2})(?P<u>[.,]\d{1,6})?'
                      r'(?P<tz>Z|[+\-]\d{2}:?\d{,2})?$'
                      )
        m = re.match(RE_ISO8601, timestr)

        if not m:
            msg = "time data '{timestr}' does not match ISO8601 format."
            raise ValueError(msg.format(timestr=timestr))

        strpfmt = '%Y-%m-%d{sep}%H:%M:%S'.format(sep=m.group('sep'))
        strpstr = timestr[:19]

        if m.group('u'):
            strpfmt += '.%f'
            strpstr += m.group('u').replace(',', '.')  # .ljust(7, '0')

        if m.group('tz'):
            if m.group('tz') == 'Z':
                strpfmt += 'Z'
                strpstr += 'Z'
            else:
                strpfmt += '%z'
                # strptime wants HHMM, without ':'
                strpstr += (m.group('tz').replace(':', '')).ljust(5, '0')

        ts = cls.strptime(strpstr, strpfmt)
        if ts.tzinfo is not None:
            ts = ts.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            # why pytest in py35/py37 fails without this?
            ts = cls._from_datetime(ts)

        return ts

    @classmethod
    def _from_posix(cls: Type['Timestamp'], timestr: str) -> 'Timestamp':
        """Convert a string in POSIX format to a Timestamp object.

        POSIX format: SECONDS[.ffffff]]
        """
        RE_POSIX = r'(?P<S>-?\d{1,13})(?:\.(?P<u>\d{1,6}))?$'  # noqa: N806
        m = re.match(RE_POSIX, timestr)

        if not m:
            msg = "time data '{timestr}' does not match POSIX format."
            raise ValueError(msg.format(timestr=timestr))

        sec = int(m.group('S'))
        usec = m.group('u')
        usec = int(usec.ljust(6, '0')) if usec else 0
        if sec < 0 and usec > 0:
            sec = sec - 1
            usec = 1000000 - usec

        ts = (cls(1970, 1, 1)
              + datetime.timedelta(seconds=sec, microseconds=usec))
        return ts

    @classmethod
    def _from_string(cls: Type['Timestamp'], timestr: str) -> 'Timestamp':
        """Convert a string to a Timestamp object."""
        handlers = [
            cls._from_mw,
            cls._from_iso8601,
            cls._from_posix,
        ]

        for handler in handlers:
            try:
                return handler(timestr)
            except ValueError:
                continue

        msg = "time data '{timestr}' does not match any format."
        raise ValueError(msg.format(timestr=timestr))

    def clone(self) -> datetime.datetime:
        """Clone this instance."""
        return self.replace(microsecond=self.microsecond)

    @classproperty
    def ISO8601Format(cls: Type['Timestamp']) -> str:  # noqa: N802
        """ISO8601 format string class property for compatibility purpose."""
        return cls._ISO8601Format()

    @classmethod
    def _ISO8601Format(cls: Type['Timestamp'],  # noqa: N802
                       sep: str = 'T') -> str:
        """ISO8601 format string.

        :param sep: one-character separator, placed between the date and time
        :return: ISO8601 format string
        """
        assert len(sep) == 1
        return '%Y-%m-%d{}%H:%M:%SZ'.format(sep)

    @classmethod
    def fromISOformat(cls: Type['Timestamp'],  # noqa: N802
                      ts: Union[str, 'Timestamp'],
                      sep: str = 'T') -> 'Timestamp':
        """Convert an ISO 8601 timestamp to a Timestamp object.

        :param ts: ISO 8601 timestamp or a Timestamp object already
        :param sep: one-character separator, placed between the date and time
        :return: Timestamp object
        """
        # If inadvertently passed a Timestamp object, use replace()
        # to create a clone.
        if isinstance(ts, cls):
            return ts.clone()
        _ts = '{pre}{sep}{post}'.format(pre=ts[:10], sep=sep, post=ts[11:])
        return cls._from_iso8601(_ts)

    @classmethod
    def fromtimestampformat(cls: Type['Timestamp'], ts: Union[str, 'Timestamp']
                            ) -> 'Timestamp':
        """Convert a MediaWiki internal timestamp to a Timestamp object."""
        # If inadvertently passed a Timestamp object, use replace()
        # to create a clone.
        if isinstance(ts, cls):
            return ts.clone()
        if len(ts) == 8:  # year, month and day are given only
            ts += '000000'
        return cls._from_mw(ts)

    def isoformat(self, sep: str = 'T') -> str:  # type: ignore[override]
        """
        Convert object to an ISO 8601 timestamp accepted by MediaWiki.

        datetime.datetime.isoformat does not postfix the ISO formatted date
        with a 'Z' unless a timezone is included, which causes MediaWiki
        ~1.19 and earlier to fail.
        """
        return self.strftime(self._ISO8601Format(sep))

    def totimestampformat(self) -> str:
        """Convert object to a MediaWiki internal timestamp."""
        return self.strftime(self.mediawikiTSFormat)

    def posix_timestamp(self) -> float:
        """
        Convert object to a POSIX timestamp.

        See Note in datetime.timestamp().
        """
        return self.replace(tzinfo=datetime.timezone.utc).timestamp()

    def posix_timestamp_format(self) -> str:
        """Convert object to a POSIX timestamp format."""
        return '{ts:.6f}'.format(ts=self.posix_timestamp())

    def __str__(self) -> str:
        """Return a string format recognized by the API."""
        return self.isoformat()

    def __add__(self, other: datetime.timedelta) -> 'Timestamp':
        """Perform addition, returning a Timestamp instead of datetime."""
        newdt = super().__add__(other)
        if isinstance(newdt, datetime.datetime):
            return self._from_datetime(newdt)
        return newdt

    def __sub__(self, other: datetime.timedelta  # type: ignore[override]
                ) -> 'Timestamp':
        """Perform subtraction, returning a Timestamp instead of datetime."""
        newdt = super().__sub__(other)
        if isinstance(newdt, datetime.datetime):
            return self._from_datetime(newdt)
        return newdt