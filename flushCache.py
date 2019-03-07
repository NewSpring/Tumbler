import requests


def flush():
    """This will flush the cache for Heighliner."""
    r = requests.post("https://apollos-api.newspring.cc/util/cache/flush")
    print(r)
