from pydantic import BaseModel
import trio

class Component(BaseModel):
    def property_order(self):
        return 10000

    def draw_property(self, nursery: trio.Nursery, entity_id: int):
        pass

    def draw_context(self, nursery: trio.Nursery, entity_id: int):
        pass