from typing import Dict
from pydantic import BaseModel
import trio

class Component(BaseModel):
    def property_order(self):
        return 10000

    def draw_property(self, nursery: trio.Nursery, entity_id: int):
        pass

    def draw_context(self, nursery: trio.Nursery, entity_id: int):
        pass
    
    def on_selected(self, nursery: trio.Nursery, entity_id: int, just_selected: bool):
        pass
    
    
    def _fix_on_load(self, new_to_old_entity_ids: Dict[int, int]):
        """This is called when the system is loaded. We don't have a guarantee that the entity ids are the same. 
        So if we have references to other entities, we need to fix them here."""
        pass