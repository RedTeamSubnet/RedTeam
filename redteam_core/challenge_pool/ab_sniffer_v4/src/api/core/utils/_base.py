# -*- coding: utf-8 -*-

import re
import copy

from pydantic import validate_call

from beans_logging import logger


@validate_call
def deep_merge(dict1: dict, dict2: dict) -> dict:
    """Return a new dictionary that's the result of a deep merge of two dictionaries.
    If there are conflicts, values from `dict2` will overwrite those in `dict1`.

    Args:
        dict1 (dict, required): The base dictionary that will be merged.
        dict2 (dict, required): The dictionary to merge into `dict1`.

    Returns:
        dict: The merged dictionary.
    """

    _merged = copy.deepcopy(dict1)
    for _key, _val in dict2.items():
        if (
            _key in _merged
            and isinstance(_merged[_key], dict)
            and isinstance(_val, dict)
        ):
            _merged[_key] = deep_merge(_merged[_key], _val)
        else:
            _merged[_key] = copy.deepcopy(_val)

    return _merged


@validate_call
def camel_to_snake(val: str) -> str:
    """Convert CamelCase to snake_case.

    Args:
        val (str): CamelCase string to convert.

    Returns:
        str: Converted snake_case string.
    """

    val = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", val)
    val = re.sub("([a-z0-9])([A-Z])", r"\1_\2", val).lower()
    return val


@validate_call
def clean_obj_dict(obj_dict: dict, cls_name: str) -> dict:
    """Clean class name from object.__dict__ for str(object).

    Args:
        obj_dict (dict, required): Object dictionary by object.__dict__.
        cls_name (str , required): Class name by cls.__name__.

    Returns:
        dict: Clean object dictionary.
    """

    try:
        if not obj_dict:
            raise ValueError("'obj_dict' argument value is empty!")

        if not cls_name:
            raise ValueError("'cls_name' argument value is empty!")
    except ValueError as err:
        logger.error(err)
        raise

    _self_dict = obj_dict.copy()
    for _key in _self_dict.copy():
        _class_prefix = f"_{cls_name}__"
        if _key.startswith(_class_prefix):
            _new_key = _key.replace(_class_prefix, "")
            _self_dict[_new_key] = _self_dict.pop(_key)
    return _self_dict


@validate_call(config={"arbitrary_types_allowed": True})
def obj_to_repr(obj: object) -> str:
    """Modifying object default repr() to custom info.

    Args:
        obj (object, required): Any python object.

    Returns:
        str: String for repr() method.
    """

    try:
        if not obj:
            raise ValueError("'obj' argument value is empty!")
    except ValueError as err:
        logger.error(err)
        raise

    _self_repr = (
        f"<{obj.__class__.__module__}.{obj.__class__.__name__} object at {hex(id(obj))}: "
        + "{"
        + f"{str(dir(obj)).replace('[', '').replace(']', '')}"
        + "}>"
    )
    return _self_repr


__all__ = [
    "deep_merge",
    "camel_to_snake",
    "clean_obj_dict",
    "obj_to_repr",
]
