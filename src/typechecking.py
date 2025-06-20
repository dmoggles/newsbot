from typing import Any, Dict

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
    except (ValueError, TypeError) as e:
        raise ValueError(f"Failed to convert to int: {e}")
    

def as_dict(value: Any) -> Dict[str, Any]:
    """    Convert a value to a dictionary, returning an empty dict if conversion fails.
    
    Args:
        value (Any): The value to convert.
    
    Returns:
        Dict[str, Any]: The converted dictionary or an empty dict if conversion fails.
    """
    try:
        return dict(value)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Failed to convert to dict: {e}")