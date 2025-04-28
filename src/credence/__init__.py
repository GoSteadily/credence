from credence import metadata


def collect_metadata(items: dict[str, str]):
    if metadata.active_adapter:
        for key, value in items.items():
            metadata.set_value(key, value)
