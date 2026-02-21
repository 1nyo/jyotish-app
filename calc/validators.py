# calc/validators.py
def prune_and_validate(obj: dict) -> dict:
    # remove keys with falsy except boolean True, and enforce 2-dec precision already done
    def _clean(x):
        if isinstance(x, dict):
            return {k:_clean(v) for k,v in x.items() if v is True or (v not in (None, False, []) and v!={})}
        elif isinstance(x, list):
            return [ _clean(v) for v in x if v is not None ]
        return x
    return _clean(obj)
