# @!documentation

#!/usr/bin/env python
"""Setup script to generate e-commerce database with 1M records."""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.generate_ecommerce_data import generate_ecommerce_database


def setup():
    """Setup e-commerce database."""
    db_path = Path(__file__).parent / "data" / "ecommerce.db"

    print("\n" + "=" * 80)
    print("Setting up E-Commerce Database")
    print("=" * 80)

    generate_ecommerce_database(db_path=str(db_path), num_records=1_000_000)

    print("\n✅ Setup Complete!")
    print("\nNext: python main.py")


if __name__ == "__main__":
    setup()
