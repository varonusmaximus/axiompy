"""
Usage Examples for File I/O Utilities

This module demonstrates various use cases for the file reading utilities.
"""

import json

from axiompy.io.file import (
    CachedReader,
    read_binary,
    read_csv,
    read_json,
    read_lines,
    read_multiple,
    read_text,
    read_with_path_expansion,
    read_yaml,
    safe_read,
)

# ==============================================================================
# Example 1: Basic Text Reading
# ==============================================================================


def example_read_text():
    """Read a simple text file"""
    # Basic usage
    content = read_text("config.txt")
    print(f"Content: {content}")

    # With default value (never raises exception)
    content = read_text("optional_config.txt", default="# default config")
    print(f"Content with default: {content}")

    # Different encoding
    content = read_text("data.txt", encoding="latin-1")


# ==============================================================================
# Example 2: JSON Configuration Files
# ==============================================================================


def example_read_json():
    """Read and parse JSON configuration files"""
    # Read JSON config
    config = read_json("config.json")
    print(f"Database: {config['database']}")
    print(f"Port: {config['port']}")

    # Safe JSON reading with default
    settings = read_json("optional_settings.json", default={}, raise_on_error=False)
    timeout = settings.get("timeout", 30)  # Use default if key missing


# ==============================================================================
# Example 3: Processing Large Log Files
# ==============================================================================


def example_read_lines():
    """Process large files line by line (memory efficient)"""
    # Process logs without loading entire file into memory
    error_count = 0
    for line in read_lines("app.log", skip_empty=True):
        if "ERROR" in line:
            error_count += 1
            print(f"Error found: {line}")

    print(f"Total errors: {error_count}")

    # Read specific lines
    first_10_lines = list(read_lines("data.txt"))[:10]


# ==============================================================================
# Example 4: CSV Data Processing
# ==============================================================================


def example_read_csv():
    """Read and process CSV files"""
    # Read CSV with headers
    users = read_csv("users.csv")
    for user in users:
        print(f"Name: {user['name']}, Age: {user['age']}")

    # Read TSV (tab-separated)
    data = read_csv("data.tsv", delimiter="\t")

    # Read headerless CSV
    raw_data = read_csv("data.csv", has_header=False)
    # Access with column_0, column_1, etc.


# ==============================================================================
# Example 5: YAML Configuration
# ==============================================================================


def example_read_yaml():
    """Read YAML configuration files"""
    # Read YAML config (requires PyYAML)
    try:
        config = read_yaml("app.yaml")
        print(f"Environment: {config['environment']}")
        print(f"Features: {config['features']}")
    except ImportError:
        print("PyYAML not installed. Install with: pip install pyyaml")


# ==============================================================================
# Example 6: Binary Files (Images, etc.)
# ==============================================================================


def example_read_binary():
    """Read binary files"""
    # Read complete binary file
    image_data = read_binary("logo.png")
    print(f"Image size: {len(image_data)} bytes")

    # Process large binary file in chunks (memory efficient)
    total_size = 0
    for chunk in read_binary("large_video.mp4", chunk_size=8192):
        total_size += len(chunk)
        # Process chunk (e.g., hash, upload, etc.)
    print(f"Total size: {total_size} bytes")


# ==============================================================================
# Example 7: Safe Reading (Never Fails)
# ==============================================================================


def example_safe_read():
    """Safely read files that might not exist"""
    # Always succeeds, never throws exceptions
    config = safe_read("config.txt", default="# default config")

    # With custom parser
    count = safe_read("count.txt", parser=int, default=0)
    data = safe_read("data.json", parser=json.loads, default={})

    # Useful in initialization code
    user_prefs = safe_read(
        "~/.myapp/preferences.json", parser=json.loads, default={"theme": "dark"}
    )


# ==============================================================================
# Example 8: Batch Reading Multiple Files
# ==============================================================================


def example_read_multiple():
    """Read multiple files at once"""
    # Read multiple text files
    files = read_multiple(["README.md", "CHANGELOG.md", "LICENSE"])

    for filepath, content in files.items():
        print(f"{filepath}: {len(content)} chars")

    # Read multiple JSON files
    configs = read_multiple(
        ["dev.json", "staging.json", "prod.json"],
        reader_func=read_json,
        fail_fast=False,  # Continue even if some files are missing
    )

    # Read with custom reader kwargs
    logs = read_multiple(["app1.log", "app2.log", "app3.log"], encoding="utf-8", default="")


# ==============================================================================
# Example 9: Path Expansion
# ==============================================================================


def example_path_expansion():
    """Read files with path expansion"""
    # Expands ~ to home directory
    bashrc = read_with_path_expansion("~/.bashrc")

    # Expands environment variables
    config = read_with_path_expansion("$HOME/.config/myapp/config.yaml")
    data = read_with_path_expansion("${DATA_DIR}/input.csv")

    # Useful for config-driven file paths
    import os

    os.environ["LOG_DIR"] = "/var/log/myapp"
    logs = read_with_path_expansion("$LOG_DIR/application.log")


# ==============================================================================
# Example 10: Cached Reading for Frequently Accessed Files
# ==============================================================================


def example_cached_reader():
    """Use caching for frequently read files"""
    # Create a cached reader with 5-minute TTL
    reader = CachedReader(ttl=300)

    # First read - from disk
    config = reader.read("config.json", parser=json.loads)

    # Subsequent reads - from cache (fast!)
    config = reader.read("config.json", parser=json.loads)
    config = reader.read("config.json", parser=json.loads)

    # Clear cache when needed
    reader.clear_cache("config.json")

    # Check cache stats
    stats = reader.get_cache_stats()
    print(f"Cached files: {stats['num_entries']}")


# ==============================================================================
# Real-World Use Cases
# ==============================================================================


def real_world_example_1():
    """Application configuration loading"""
    # Load config with fallbacks
    config = safe_read(
        "config.json",
        parser=json.loads,
        default={"debug": False, "port": 8000, "database": "sqlite:///app.db"},
    )

    # Override with environment-specific config
    env_config = safe_read(f"config.{config.get('env', 'dev')}.json", parser=json.loads, default={})
    config.update(env_config)

    return config


def real_world_example_2():
    """Log analysis"""
    # Analyze large log file efficiently
    stats = {"total_lines": 0, "errors": 0, "warnings": 0, "unique_ips": set()}

    for line in read_lines("access.log", skip_empty=True):
        stats["total_lines"] += 1

        if "ERROR" in line:
            stats["errors"] += 1
        elif "WARNING" in line:
            stats["warnings"] += 1

        # Extract IP (simplified)
        if line.startswith("["):
            ip = line.split()[0].strip("[]")
            stats["unique_ips"].add(ip)

    print(f"Total lines: {stats['total_lines']}")
    print(f"Errors: {stats['errors']}")
    print(f"Warnings: {stats['warnings']}")
    print(f"Unique IPs: {len(stats['unique_ips'])}")


def real_world_example_3():
    """Data pipeline"""
    # Read CSV data
    raw_data = read_csv("input.csv")

    # Process and transform
    processed_data = []
    for row in raw_data:
        processed_data.append(
            {"id": int(row["id"]), "value": float(row["value"]), "status": row["status"].lower()}
        )

    # Save results
    with open("output.json", "w") as f:
        json.dump(processed_data, f, indent=2)


def real_world_example_4():
    """Configuration management with caching"""
    # Global cached reader for app lifetime
    config_reader = CachedReader(ttl=300)  # 5 minutes

    def get_database_config():
        """Get database config (cached)"""
        return config_reader.read("database.yaml", parser=yaml.safe_load)

    def get_feature_flags():
        """Get feature flags (cached)"""
        return config_reader.read("features.json", parser=json.loads)

    # These calls are fast after first read
    db_config = get_database_config()
    features = get_feature_flags()

    # Force refresh if needed
    config_reader.clear_cache()


def real_world_example_5():
    """Multi-environment configuration"""
    import os

    env = os.getenv("APP_ENV", "dev")

    # Read multiple config files
    configs = read_multiple(
        ["config.base.json", f"config.{env}.json", "config.local.json"],  # Optional overrides
        reader_func=read_json,
        fail_fast=False,  # Continue if optional files missing
    )

    # Merge configs (later ones override earlier)
    final_config = {}
    for config_path in sorted(configs.keys()):
        final_config.update(configs[config_path])

    return final_config


# ==============================================================================
# Performance Comparison
# ==============================================================================


def performance_comparison():
    """Compare different reading approaches"""
    import time

    # Traditional approach
    start = time.time()
    with open("large_file.txt") as f:
        content = f.read()
    traditional_time = time.time() - start

    # Using read_text
    start = time.time()
    content = read_text("large_file.txt")
    utility_time = time.time() - start

    # Memory-efficient line reading
    start = time.time()
    line_count = sum(1 for _ in read_lines("large_file.txt"))
    generator_time = time.time() - start

    print(f"Traditional: {traditional_time:.4f}s")
    print(f"read_text: {utility_time:.4f}s")
    print(f"read_lines: {generator_time:.4f}s")


# ==============================================================================
# Error Handling Patterns
# ==============================================================================


def error_handling_patterns():
    """Different error handling approaches"""

    # Pattern 1: Use default value
    config = read_text("config.txt", default="{}")

    # Pattern 2: Explicit try-catch
    try:
        config = read_json("config.json")
    except FileNotFoundError:
        print("Config not found, using defaults")
        config = {}

    # Pattern 3: Safe read (never raises)
    config = safe_read("config.json", parser=json.loads, default={})

    # Pattern 4: Graceful degradation
    configs = read_multiple(
        ["primary.json", "fallback.json", "defaults.json"], reader_func=read_json, fail_fast=False
    )
    # Use first available config
    for path in ["primary.json", "fallback.json", "defaults.json"]:
        if path in configs:
            config = configs[path]
            break


if __name__ == "__main__":
    print("File I/O Utilities - Usage Examples")
    print("=" * 50)
    print("\nSee function definitions above for detailed examples.")
    print("\nKey utilities:")
    print("  - read_text()        : Simple text files")
    print("  - read_json()        : JSON configuration")
    print("  - read_lines()       : Memory-efficient line reading")
    print("  - read_csv()         : CSV data files")
    print("  - read_yaml()        : YAML configuration")
    print("  - read_binary()      : Binary files and images")
    print("  - safe_read()        : Never-fail reading")
    print("  - read_multiple()    : Batch file reading")
    print("  - read_with_path_expansion() : ~/ and $ENV support")
    print("  - CachedReader       : Cached file reading")
