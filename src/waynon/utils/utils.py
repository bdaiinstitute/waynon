# Part of ImGui Bundle - MIT License - Copyright (c) 2022-2023 Pascal Thomet - https://github.com/pthom/imgui_bundle
from typing import Callable, TypeVar, Any
from pathlib import Path
from contextlib import contextmanager
from imgui_bundle import imgui
import trio

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


# def cancellable
class Cancellable:
    def __init__(self, nursery: trio.Nursery, name: str, coroutine, *args):
        self.name = name
        self.nursery = nursery  
        self.coroutine = coroutine
        self.args = args
        self.running = False

    async def run(self):
        self.running = True
        with trio.CancelScope() as self.scope:
            await self.coroutine(*self.args)
        self.running = False
    
    def draw(self, size = None):
        if self.running:
            if imgui.button(f"Cancel", size):
                self.scope.cancel()
        else:
            if imgui.button(f"{self.name}", size):
                self.nursery.start_soon(self.run)

class LongTask:
    def __init__(self, nursery: trio.Nursery, name: str, coroutine, *args):
        self.name = name
        self.nursery = nursery  
        self.coroutine = coroutine
        self.args = args
        self.running = False
    
    async def run(self):
        self.running = True
        await self.coroutine(*self.args)
        self.running = False
    
    def draw(self, size = None):
        if self.running:
            imgui.begin_disabled()
            if imgui.button(f"Busy", size):
                pass
            imgui.end_disabled()
        else:
            if imgui.button(f"{self.name}", size):
                self.nursery.start_soon(self.run)

        


COLORS = {
    "BLUE": (0.0, 0.5843, 1.0, 1.0),
    "YELLOW": (1.0, 0.8, 0.0, 1.0),
    "RED": (0.835, 0.368, 0.0, 1.0),
    "GREEN": (0.008, 0.6186, 0.45098, 1.0),
    "PURPLE": (0.51372, 0.298, 0.49012, 1.0),
    "ORANGE": (1.0, 0.4, 0.0, 1.0),
}

ASSET_PATH = Path(__file__).parents[3] / "assets"


assert ASSET_PATH.exists(), f"ASSET_PATH {ASSET_PATH} does not exist"

