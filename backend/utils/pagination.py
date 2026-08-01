def page_offset(page: int, page_size: int) -> int:
    """Convert a validated one-based page number into a SQL offset."""
    return (page - 1) * page_size
