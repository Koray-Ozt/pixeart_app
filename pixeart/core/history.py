from abc import ABC, abstractmethod
from typing import List, Callable

class Command(ABC):
    @property
    def name(self) -> str:
        return getattr(self, "_name", "Unknown Command")
        
    @name.setter
    def name(self, val: str):
        self._name = val

    @abstractmethod
    def execute(self) -> None:
        pass
        
    @abstractmethod
    def undo(self) -> None:
        pass

class History:
    def __init__(self, max_steps: int = 50):
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []
        self.max_steps = max_steps
        self._callbacks: List[Callable[[], None]] = []
        
    def register_callback(self, callback: Callable[[], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify(self) -> None:
        for cb in self._callbacks:
            cb()

    def execute(self, command: Command) -> None:
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        if len(self._undo_stack) > self.max_steps:
            self._undo_stack.pop(0)
            
        self._notify()
            
    def undo(self) -> bool:
        if not self._undo_stack:
            return False
            
        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)
        
        self._notify()
        return True
        
    def redo(self) -> bool:
        if not self._redo_stack:
            return False
            
        command = self._redo_stack.pop()
        command.execute()
        self._undo_stack.append(command)
        
        self._notify()
        return True
        
    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._notify()

    @property
    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    @property
    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    @property
    def undo_count(self) -> int:
        return len(self._undo_stack)
        
    @property
    def redo_count(self) -> int:
        return len(self._redo_stack)
