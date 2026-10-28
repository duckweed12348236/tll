import asyncio
import sys

from config import GRPC_PORT
from protocols import serve

if __name__ == "__main__":
    asyncio.run(serve(int(sys.argv[1]) if len(sys.argv) > 1 else GRPC_PORT))
