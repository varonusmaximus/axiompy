"""
Examples demonstrating the axiompy.data module for data engineering.

This example shows how to use all the major features of the data engineering
module with both Pandas (local development) and notes on Spark usage (production).
"""

from datetime import datetime

import pandas as pd

# Import axiompy.data utilities
from axiompy.data import (
    BatchProcessorFactory,
    ChangeDetectorFactory,
    CompressionFormat,
    DataCompressor,
    DataExpectation,
    DataFormat,
    DataProfilerFactory,
    DataTransformerFactory,
    FormatConverter,
    LineageTrackerFactory,
    Pipeline,
    Task,
)

# Import axiompy utilities
from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)


# ============================================================================
# Example 1: Data Quality Profiling and Validation
# ============================================================================


def example_data_quality():
    """Demonstrate data quality profiling and validation."""
    logger.info("=" * 60)
    logger.info("Example 1: Data Quality Profiling and Validation")
    logger.info("=" * 60)

    # Create sample data
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, None, 7, 8],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry"],
            "age": [25, 30, None, 45, 28, 35, 42, None],
            "email": [
                "alice@example.com",
                "bob@example.com",
                "charlie@example.com",
                "invalid-email",
                "eve@example.com",
                "frank@example.com",
                "grace@example.com",
                "henry@example.com",
            ],
            "status": [
                "active",
                "active",
                "inactive",
                "active",
                "pending",
                "active",
                "active",
                "inactive",
            ],
        }
    )

    # Auto-detect engine and create profiler
    profiler = DataProfilerFactory.create_auto(df)

    # Profile the data
    report = profiler.profile(df)

    logger.info(f"Row count: {report.row_count}")
    logger.info(f"Column count: {report.column_count}")
    logger.info(f"Null counts: {report.null_counts}")
    logger.info(f"Duplicate count: {report.duplicate_count}")
    logger.info(f"Quality issues found: {len(report.issues)}")

    for issue in report.issues:
        logger.warning(
            f"  {issue['severity'].upper()}: {issue['issue']} in column '{issue['column']}'"
        )

    # Define data quality expectations
    expectations = [
        DataExpectation(name="user_id_not_null", column="user_id", condition="not_null"),
        DataExpectation(name="user_id_unique", column="user_id", condition="unique"),
        DataExpectation(
            name="age_range", column="age", condition="in_range", params={"min": 0, "max": 150}
        ),
        DataExpectation(
            name="status_valid",
            column="status",
            condition="in_set",
            params={"values": ["active", "inactive", "pending"]},
        ),
    ]

    # Validate expectations
    results = profiler.validate_expectations(df, expectations)

    logger.info("\nValidation Results:")
    logger.info(f"  Passed: {results['passed']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info(f"  Success: {results['success']}")

    for detail in results["details"]:
        status = "✓" if detail["passed"] else "✗"
        logger.info(f"  {status} {detail['expectation']}: {detail['message']}")

    # Check schema
    expected_schema = {
        "user_id": "int",
        "name": "string",
        "age": "int",
        "email": "string",
        "status": "string",
    }

    schema_check = profiler.check_schema(df, expected_schema)
    logger.info(f"\nSchema validation: {'Valid' if schema_check['valid'] else 'Invalid'}")
    if not schema_check["valid"]:
        for issue in schema_check["issues"]:
            logger.warning(f"  Schema issue: {issue}")


# ============================================================================
# Example 2: Data Transformations
# ============================================================================


def example_transformations():
    """Demonstrate common data transformations."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 2: Data Transformations")
    logger.info("=" * 60)

    # Create sample data
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, 5, 7, 8],
            "first_name": ["Alice", "Bob", "Charlie", "David", "Eve", "Eve", "Grace", "Henry"],
            "last_name": ["Smith", "Jones", None, "Wilson", "Brown", "Brown", "Taylor", "Davis"],
            "age": [25, 30, None, 45, 28, 28, 42, None],
            "score": [85.5, 92.0, None, 78.5, 95.0, 95.0, 88.0, None],
        }
    )

    logger.info(f"Original data shape: {df.shape}")

    # Create transformer
    transformer = DataTransformerFactory.create_auto(df)

    # Rename columns
    df = transformer.rename_columns(df, {"first_name": "fname", "last_name": "lname"})
    logger.info("Renamed columns: first_name → fname, last_name → lname")

    # Fill nulls with strategy
    df = transformer.fill_nulls(df, strategy="mean", columns=["age", "score"])
    logger.info("Filled null ages and scores with mean values")

    # Fill remaining nulls with value
    df = transformer.fill_nulls(df, strategy="value", value="Unknown", columns=["lname"])
    logger.info("Filled null last names with 'Unknown'")

    # Remove duplicates
    original_count = len(df)
    df = transformer.deduplicate(df, subset=["user_id", "fname"])
    logger.info(f"Removed duplicates: {original_count} → {len(df)} rows")

    # Filter rows
    df = transformer.filter_rows(df, "age >= 30")
    logger.info(f"Filtered to age >= 30: {len(df)} rows remaining")

    # Add computed column
    df = transformer.add_computed_column(df, "full_name", lambda d: d["fname"] + " " + d["lname"])
    logger.info("Added computed column: full_name")

    # Cast column
    df = transformer.cast_column(df, "age", "int")
    logger.info("Cast age to int")

    logger.info(f"\nFinal data shape: {df.shape}")
    logger.info(f"Columns: {list(df.columns)}")


# ============================================================================
# Example 3: Batch Processing
# ============================================================================


def example_batch_processing():
    """Demonstrate batch processing for large datasets."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 3: Batch Processing")
    logger.info("=" * 60)

    # Create large sample dataset
    df = pd.DataFrame(
        {
            "id": range(1, 10001),
            "value": range(10000, 20000),
            "category": ["A", "B", "C"] * 3333 + ["A"],
        }
    )

    logger.info(f"Processing {len(df)} rows in batches")

    # Create batch processor
    processor = BatchProcessorFactory.create_auto(
        df,
        batch_size=1000,
        max_workers=2,  # Parallel processing
        show_progress=False,  # Set to True if tqdm is installed
    )

    # Define transformation function
    def transform_batch(batch):
        """Transform each batch - your custom logic here."""
        batch["value_squared"] = batch["value"] ** 2
        batch["category_upper"] = batch["category"].str.upper()
        return batch

    # Process batches
    processed_batches = []

    def sink(batch):
        """Sink function to collect results."""
        processed_batches.append(batch)

    results = processor.process_batches(
        data=df, transform_func=transform_batch, sink=sink, fail_fast=False
    )

    logger.info(f"Batches processed: {results['batches_processed']}")
    logger.info(f"Batches failed: {results['batches_failed']}")
    logger.info(f"Total batches collected: {len(processed_batches)}")

    # Combine results
    final_df = pd.concat(processed_batches, ignore_index=True)
    logger.info(f"Final DataFrame shape: {final_df.shape}")


# ============================================================================
# Example 4: ETL Pipeline
# ============================================================================


def example_pipeline():
    """Demonstrate building and running an ETL pipeline."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 4: ETL Pipeline")
    logger.info("=" * 60)

    # Define extract task
    def extract():
        logger.info("Extracting data from source...")
        df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "value": [10, 20, None, 40, 50],
                "status": ["active", "inactive", "active", "active", "inactive"],
            }
        )
        return df

    # Define transform task
    def transform(context):
        logger.info("Transforming data...")
        df = context["extract"]
        transformer = DataTransformerFactory.create_auto(df)

        # Clean data
        df = transformer.fill_nulls(df, strategy="mean", columns=["value"])
        df = transformer.filter_rows(df, "status == 'active'")

        return df

    # Define load task
    def load(context):
        logger.info("Loading data to target...")
        df = context["transform"]
        # In real scenario, write to database or file
        logger.info(f"Loaded {len(df)} rows to target")
        return {"rows_loaded": len(df)}

    # Create pipeline
    pipeline = Pipeline("simple_etl")

    # Add tasks
    extract_task = Task(name="extract", func=extract)
    transform_task = Task(name="transform", func=transform, depends_on=["extract"])
    load_task = Task(name="load", func=load, depends_on=["transform"])

    pipeline.add_tasks([extract_task, transform_task, load_task])

    # Visualize pipeline
    logger.info("\nPipeline Structure:")
    logger.info(pipeline.visualize())

    # Run pipeline
    logger.info("\nExecuting pipeline...")
    results = pipeline.run(fail_fast=True)

    if results["success"]:
        logger.info("✓ Pipeline completed successfully!")
        for task_name, task_result in results["tasks"].items():
            logger.info(f"  {task_name}: {task_result['status']} ({task_result['duration']:.2f}s)")
    else:
        logger.error("✗ Pipeline failed!")
        for error in results["errors"]:
            logger.error(f"  {error['task']}: {error['error']}")


# ============================================================================
# Example 5: Change Data Capture (CDC)
# ============================================================================


def example_change_detection():
    """Demonstrate detecting changes between datasets."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 5: Change Data Capture (CDC)")
    logger.info("=" * 60)

    # Old dataset (yesterday)
    old_df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
            "score": [85, 90, 75, 88, 92],
        }
    )

    # New dataset (today)
    new_df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 5, 6],  # 4 deleted, 6 added
            "name": ["Alice", "Bob Smith", "Charlie", "Eve", "Frank"],  # Bob's name changed
            "score": [85, 90, 80, 92, 78],  # Charlie's score changed
        }
    )

    # Create change detector
    detector = ChangeDetectorFactory.create_auto(old_df, key_columns=["user_id"])

    # Detect all changes
    changes = detector.detect_changes(old_df, new_df)

    logger.info("Change Detection Results:")
    logger.info(f"  Inserts: {changes['summary']['inserts_count']}")
    logger.info(f"  Updates: {changes['summary']['updates_count']}")
    logger.info(f"  Deletes: {changes['summary']['deletes_count']}")
    logger.info(f"  Unchanged: {changes['summary']['unchanged_count']}")

    logger.info("\nInserted records:")
    logger.info(f"{changes['inserts']}")

    logger.info("\nUpdated records:")
    logger.info(f"{changes['updates']}")

    logger.info("\nDeleted records:")
    logger.info(f"{changes['deletes']}")


# ============================================================================
# Example 6: Format Conversion
# ============================================================================


def example_format_conversion():
    """Demonstrate converting between data formats."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 6: Format Conversion")
    logger.info("=" * 60)

    # Create sample data
    df = pd.DataFrame(
        {"id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"], "value": [100, 200, 300]}
    )

    # Create converter
    converter = FormatConverter()

    # Convert to different formats
    logger.info("Converting DataFrame to various formats...")

    # CSV
    csv_bytes = converter.convert(df, DataFormat.CSV, DataFormat.CSV, output_path=None)
    logger.info(f"CSV size: {len(csv_bytes)} bytes")

    # JSON
    json_bytes = converter.convert(df, DataFormat.CSV, DataFormat.JSON, output_path=None)
    logger.info(f"JSON size: {len(json_bytes)} bytes")

    # Parquet (smallest)
    parquet_bytes = converter.convert(df, DataFormat.CSV, DataFormat.PARQUET, output_path=None)
    logger.info(f"Parquet size: {len(parquet_bytes)} bytes")

    logger.info("\nParquet is typically the most efficient format for analytics!")


# ============================================================================
# Example 7: Data Compression
# ============================================================================


def example_compression():
    """Demonstrate data compression."""
    logger.info("\n" + "=" * 60)
    logger.info("Example 7: Data Compression")
    logger.info("=" * 60)

    # Create some sample data to compress
    data = "Hello, this is sample data to compress! " * 100
    data_bytes = data.encode("utf-8")

    logger.info(f"Original size: {len(data_bytes)} bytes")

    # Create compressor
    compressor = DataCompressor()

    # Compare compression formats
    logger.info("\nComparing compression formats:")
    results = compressor.compare_formats(data_bytes)

    for format_name, stats in results.items():
        if "error" not in stats:
            logger.info(
                f"  {format_name}: {stats['compressed_size']} bytes "
                f"({stats['compression_ratio']:.1f}% reduction)"
            )
        else:
            logger.info(f"  {format_name}: {stats['error']}")

    # Compress and decompress
    compressed = compressor.compress(data_bytes, format=CompressionFormat.GZIP)
    decompressed = compressor.decompress(compressed, format=CompressionFormat.GZIP)

    assert decompressed == data_bytes, "Decompression failed!"
    logger.info("\n✓ Compression/decompression verified!")


# ============================================================================
# Example 8: Complete Workflow (Spark-compatible code)
# ============================================================================


def example_complete_workflow():
    """
    Demonstrate a complete data engineering workflow.

    This code works with Pandas locally and can be adapted for Spark
    by simply changing the data source to a Spark DataFrame.
    """
    logger.info("\n" + "=" * 60)
    logger.info("Example 8: Complete Data Engineering Workflow")
    logger.info("=" * 60)

    # Step 1: Extract data
    logger.info("Step 1: Extracting data...")
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5, 5, 7, 8, None, 10],
            "name": [
                "Alice",
                "Bob",
                "Charlie",
                "David",
                "Eve",
                "Eve",
                "Grace",
                "Henry",
                "Ivy",
                "Jack",
            ],
            "age": [25, 30, None, 45, 28, 28, 42, None, 35, 50],
            "email": [
                "alice@example.com",
                "bob@example.com",
                "charlie@example.com",
                "david@example.com",
                "eve@example.com",
                "eve@example.com",
                "grace@example.com",
                "henry@example.com",
                "ivy@example.com",
                "jack@example.com",
            ],
            "score": [85.5, 92.0, None, 78.5, 95.0, 95.0, 88.0, None, 91.0, 76.0],
            "created_at": pd.date_range("2024-10-01", periods=10, freq="D"),
        }
    )

    logger.info(f"Extracted {len(df)} rows")

    # Step 2: Profile data quality
    logger.info("\nStep 2: Profiling data quality...")
    profiler = DataProfilerFactory.create_auto(df)
    report = profiler.profile(df)
    logger.info(f"  Quality issues: {len(report.issues)}")

    # Step 3: Transform data
    logger.info("\nStep 3: Transforming data...")
    transformer = DataTransformerFactory.create_auto(df)

    # Clean nulls
    df = transformer.fill_nulls(df, strategy="mean", columns=["age", "score"])
    df = transformer.drop_nulls(df, subset=["user_id"])

    # Remove duplicates
    df = transformer.deduplicate(df, subset=["user_id"])
    logger.info(f"  After cleaning: {len(df)} rows")

    # Step 4: Validate quality
    logger.info("\nStep 4: Validating data quality...")
    expectations = [
        DataExpectation(name="user_id_not_null", column="user_id", condition="not_null"),
        DataExpectation(name="user_id_unique", column="user_id", condition="unique"),
    ]
    validation = profiler.validate_expectations(df, expectations)
    logger.info(f"  Validation: {validation['passed']}/{len(expectations)} passed")

    # Step 5: Track lineage
    logger.info("\nStep 5: Tracking lineage...")
    tracker = LineageTrackerFactory.create_auto(df)
    tracker.track_transformation(
        job_name="user_data_cleanup",
        input_sources=["raw_users"],
        output_targets=["clean_users"],
        transformation="Remove nulls, fill missing values, deduplicate",
        data_in=None,  # Would pass original df here
        data_out=df,
        metadata={"env": "dev", "timestamp": datetime.now().isoformat()},
    )
    logger.info("  Lineage tracked")

    # Step 6: Save results
    logger.info("\nStep 6: Saving results...")
    logger.info(f"  Final dataset: {len(df)} rows × {len(df.columns)} columns")
    logger.info("  Ready for loading to target system")

    logger.info("\n✓ Complete workflow finished successfully!")


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    logger.info("Starting axiompy.data examples...")
    logger.info("These examples demonstrate the data engineering module features\n")

    try:
        # Run all examples
        example_data_quality()
        example_transformations()
        example_batch_processing()
        example_pipeline()
        example_change_detection()
        example_format_conversion()
        example_compression()
        example_complete_workflow()

        logger.info("\n" + "=" * 60)
        logger.info("All examples completed successfully!")
        logger.info("=" * 60)

        logger.info("\nNote: These examples use Pandas for demonstration.")
        logger.info("The same code works with Spark DataFrames in Databricks!")
        logger.info("Just change the data source and the engine will auto-detect.")

    except Exception as e:
        logger.error(f"Example failed: {e}", exc_info=True)
