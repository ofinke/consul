import importlib.util
import inspect
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, Callable, Dict


class PromptFormatRegistry:
    def __init__(self):
        self._functions: Dict[str, Callable] = {}
        self._modules_to_discover = []
    
    def register(self, name: str = None):
        """Decorator to register a function"""
        def decorator(func: Callable) -> Callable:
            register_name = name or func.__name__
            self._functions[register_name] = func
            return func
        return decorator
    
    def add_module(self, module_name: str):
        """Add a module to be discovered"""
        if module_name not in self._modules_to_discover:
            self._modules_to_discover.append(module_name)
    
    def discover_modules(self):
        """Import specified modules to trigger registration"""
        for module_name in self._modules_to_discover:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                print(f"Warning: Could not import {module_name}: {e}")
    
    def get_values(self, **kwargs) -> Dict[str, Any]:
        """Get all function results"""
        # Ensure modules are discovered
        self.discover_modules()
        
        results = {}
        for name, func in self._functions.items():
            try:
                sig = inspect.signature(func)
                
                if sig.parameters:
                    # Filter kwargs to only include what the function expects
                    func_kwargs = {}
                    for param_name in sig.parameters:
                        if param_name in kwargs:
                            func_kwargs[param_name] = kwargs[param_name]
                    
                    results[name] = func(**func_kwargs)
                else:
                    results[name] = func()
                    
            except Exception as e:
                results[name] = f"Error: {str(e)}"
        
        return results
    
    def format_string(self, template: str, **kwargs) -> str:
        """Format string with function results"""
        values = self.get_values(**kwargs)
        return template.format(**values)

# Global registry instance
prompt_format_registry = PromptFormatRegistry()

print(prompt_format_registry.get_values())