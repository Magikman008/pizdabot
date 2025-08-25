import asyncio

from app.app import main
from app.db import init_db

if __name__ == "__main__":
    init_db()

    asyncio.run(main())
