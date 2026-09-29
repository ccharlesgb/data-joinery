import traceback

from data_joinery import transform

try:

    @transform
    def count_labels(labels: list[str]) -> int:
        return len(labels)

except TypeError:
    print(traceback.format_exc(limit=1))
