from credence import metadata


def collect_metadata(path: str, value: str):
    if metadata.active_adapter:
        metadata.set_value(path, value)
