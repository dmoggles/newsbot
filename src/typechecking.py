from typing import Any, Dict, TypeVar, Type, Optional, overload, cast

T = TypeVar("T")


def as_int(value: Any) -> int:
    """
    Convert a value to an integer, returning 0 if conversion fails.

    Args:
        value (Any): The value to convert.

    Returns:
        int: The converted integer or 0 if conversion fails.
    """
    try:
        return int(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Failed to convert to int: {value}") from exc


def as_dict(value: Any) -> Dict[str, Any]:
    """Convert a value to a dictionary, returning an empty dict if conversion fails.

    Args:
        value (Any): The value to convert.

    Returns:
        Dict[str, Any]: The converted dictionary or an empty dict if conversion fails.
    """
    try:
        return dict(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Failed to convert to dict: {value}") from exc


@overload
def as_str_key_dict(value: Any) -> Dict[str, Any]: ...


@overload
def as_str_key_dict(value: Any, value_type: Type[T]) -> Dict[str, T]: ...


def as_str_key_dict(value: Any, value_type: Optional[Type[T]] = None) -> Dict[str, Any]:
    """
    Convert a value to a dictionary with string keys, optionally validating value types.

    Args:
        value (Any): The value to convert to a dictionary.
        value_type (Optional[Type[T]]): Optional type to validate dictionary values against.

    Returns:
        Dict[str, T]: The converted dictionary with string keys and optionally typed values.

    Raises:
        ValueError: If conversion fails or if value_type is specified and values don't match.

    Examples:
        # Basic usage - returns Dict[str, Any]
        result = as_str_key_dict({"a": 1, "b": 2})

        # With type validation - returns Dict[str, int]
        result = as_str_key_dict({"a": 1, "b": 2}, int)

        # Type validation will raise ValueError if types don't match
        result = as_str_key_dict({"a": 1, "b": "hello"}, int)  # Raises ValueError
    """
    try:
        # First convert to dict
        result_dict = dict(value)

        # Ensure all keys are strings
        str_key_dict: Dict[str, T | None] = {}
        for key, val in result_dict.items():
            str_key = str(key)  # If value_type is specified, validate each value
            if value_type is not None:
                if not isinstance(val, value_type):
                    # Allow None values and lists even if value_type is specified
                    if val is not None and not isinstance(val, (list, tuple)):
                        raise ValueError(f"Value {val!r} is not of type {value_type.__name__}")

            str_key_dict[str_key] = cast(T, val)

        return str_key_dict

    except (ValueError, TypeError) as exc:
        raise ValueError(f"Failed to convert to string-keyed dict: {value}") from exc
