# -*- coding: utf-8 -*-

from pydantic import BaseModel, ConfigDict

# from api.core import utils


class BasePM(BaseModel):
    # model_config = ConfigDict(json_encoders={datetime: utils.datetime_to_iso})
    pass


class ExtraBasePM(BasePM):
    model_config = ConfigDict(extra="allow")


__all__ = [
    "BasePM",
    "ExtraBasePM",
]
