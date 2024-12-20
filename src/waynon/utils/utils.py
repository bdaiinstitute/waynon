# Part of ImGui Bundle - MIT License - Copyright (c) 2022-2023 Pascal Thomet - https://github.com/pthom/imgui_bundle
from typing import Callable, TypeVar, Any
from pathlib import Path
from contextlib import contextmanager

# Create type variables for the argument and return types of the function
A = TypeVar("A", bound=Callable[..., Any])
R = TypeVar("R")


def static(**kwargs: Any) -> Callable[[A], A]:
    """A decorator that adds static variables to a function
    :param kwargs: list of static variables to add
    :return: decorated function

    Example:
        @static(x=0, y=0)
        def my_function():
            # static vars are stored as attributes of "my_function"
            # we use static as a more readable synonym.
            static = my_function

            static.x += 1
            static.y += 2
            print(f"{static.f.x}, {static.f.x}")

        invoking f three times would print 1, 2 then 2, 4, then 3, 6

    Static variables are similar to global variables, with the same shortcomings!
    Use them only in small scripts, not in production code!
    """

    def decorator(func: A) -> A:
        for key, value in kwargs.items():
            setattr(func, key, value)
        return func

    return decorator


@contextmanager
def callback_controller(static):
    static.busy = True
    yield
    static.busy = False

def one_at_a_time(static):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            if static.busy:
                return
            with callback_controller(static):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


COLORS = {
    "BLUE": [0.0, 0.5843, 1.0, 1.0],
    "YELLOW": [1.0, 0.8, 0.0, 1.0],
    "RED": [0.835, 0.368, 0.0, 1.0],
    "GREEN": [0.008, 0.6186, 0.45098, 1.0],
    "PURPLE": [0.51372, 0.298, 0.49012, 1.0],
    "ORANGE": [1.0, 0.4, 0.0, 1.0],
}

ASSET_PATH = Path(__file__).parents[3] / "assets"
DATA_PATH = Path(__file__).parents[3] / "data"

assert ASSET_PATH.exists(), f"ASSET_PATH {ASSET_PATH} does not exist"
assert DATA_PATH.exists(), f"DATA_PATH {DATA_PATH} does not exist"

