from credence import metadata


def collect_metadata(items: dict[str, str]):
    if metadata.active_adapter:
        for key, value in items.items():
            if not isinstance(value, str):
                try:
                    metadata.set_value(key, str(value))
                except Exception as e:
                    raise Exception("`collect_metadata` could not convert value into str") from e
            else:
                metadata.set_value(key, value)
