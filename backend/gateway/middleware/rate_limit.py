from fastapi import Request


async def no_op_rate_limit(_: Request) -> None:
    return
