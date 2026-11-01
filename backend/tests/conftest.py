import os
import sys
import types

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

try:
    import websockets
    if not hasattr(websockets, "asyncio"):
        asyncio_mod = types.ModuleType("websockets.asyncio")
        client_mod = types.ModuleType("websockets.asyncio.client")
        client_mod.ClientConnection = object
        asyncio_mod.client = client_mod
        websockets.asyncio = asyncio_mod
        sys.modules["websockets.asyncio"] = asyncio_mod
        sys.modules["websockets.asyncio.client"] = client_mod
except ImportError:
    pass
