import json


def check_context_capacity(messages: list[dict], tools: list[dict], capacity: int | None,
                           *, requires_full_text=False, reserve=4096):
    if capacity is None:
        return
    # Conservative UTF-8 byte budgeting for arbitrary compatible models.
    upper_bound = len(json.dumps(messages, ensure_ascii=False).encode())
    upper_bound += len(json.dumps(tools, ensure_ascii=False).encode()) + 64 * len(messages)
    if upper_bound + reserve > capacity:
        raise ValueError("CONTEXT_CAPACITY_EXCEEDED")
