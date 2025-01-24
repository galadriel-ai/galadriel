import datetime


def get_current_timestamp() -> int:
    return int(datetime.datetime.now(datetime.timezone.utc).timestamp())


def format_timestamp(timestamp: int) -> str:
    now = get_current_timestamp()  # Current timestamp in seconds
    diff = now - timestamp  # Difference in seconds
    abs_diff = abs(diff)

    seconds = int(abs_diff)
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if abs_diff < 60:
        return "just now"
    elif minutes < 60:
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        return f"{days} day{'s' if days != 1 else ''} ago"
