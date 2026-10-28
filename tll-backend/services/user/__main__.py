import asyncio
import sys

from services.user.app import serve
from services.user.config import GRPC_PORT

if __name__ == "__main__":
    try:
        asyncio.run(serve(int(sys.argv[1]) if len(sys.argv) > 1 else GRPC_PORT))
    except KeyboardInterrupt:
        pass
