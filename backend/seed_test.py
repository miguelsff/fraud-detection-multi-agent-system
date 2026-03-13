#!/usr/bin/env python
"""Entry point for seed and test synthetic data."""

import asyncio
from scripts.seed_service import main

if __name__ == "__main__":
    asyncio.run(main())
