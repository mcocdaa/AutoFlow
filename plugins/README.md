# AutoFlow Plugin System

This directory contains plugins for AutoFlow. Plugins are Python modules that extend the functionality of the core engine.

## Plugin Structure

A standard plugin structure:

```
my_plugin/
  __init__.py       # Plugin metadata and exports
  actions.py        # Automation actions
  config.py         # Plugin configuration schema
  README.md         # Plugin documentation
```

## Plugin Types

1. **Action Plugins**: Extend automation capabilities (e.g., OCR, PDF manipulation).
2. **Device Plugins**: Add support for new devices/drivers.
3. **Function Plugins**: Add business logic or integrations.
