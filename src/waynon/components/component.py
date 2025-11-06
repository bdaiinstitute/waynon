# Copyright (c) 2025 Robotics and AI Institute LLC dba RAI Institute. All rights reserved.

from typing import Dict
from dataclasses import dataclass
from pydantic import BaseModel
import trio

@dataclass
class ValidityResult:
    _valid: bool = True
    _message: str = ""

    def __bool__(self):
        return self._valid
    
    def __str__(self):
        return self._message
    
    @staticmethod
    def invalid(message: str = ""):
        return ValidityResult(_valid=False, _message=message)
    
    @staticmethod
    def valid():
        return ValidityResult(True)
    
    def __repr__(self):
        return f"ValidityResult({self._valid}, {self._message})"

class Component(BaseModel):
    def property_order(self):
        return 10000

    def draw_property(self, nursery: trio.Nursery, entity_id: int):
        pass

    def draw_context(self, nursery: trio.Nursery, entity_id: int):
        pass
    
    def on_selected(self, nursery: trio.Nursery, entity_id: int, just_selected: bool):
        pass
    
    @staticmethod
    def default_name():
        return "Node"
    
    def valid(self):
        return ValidityResult.valid()
    
    def _fix_on_load(self, new_to_old_entity_ids: Dict[int, int]):
        """This is called when the system is loaded. We don't have a guarantee that the entity ids are the same. 
        So if we have references to other entities, we need to fix them here."""
        pass
    
    def on_load(self, entity_id: int):
        """This is called when the component is initialized. Can be used to make sure everything is in order."""
        pass
