# @!documentation

"""
Real-world streaming examples using axiompy.data.streaming.

Examples demonstrating practical use cases for streaming data processing.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
from axiompy.data import DataProfilerFactory, DataTransformerFactory
from axiompy.data.streaming import StreamConsumerFactory, StreamHandler, StreamProducerFactory
from axiompy.data.streaming.types import StreamEngine, StreamMessage, StreamSettings

from axiompy.loggers import LoggerFactory

logger = LoggerFactory.create_logger(__name__)


# =============================================================================
# Example 1: Basic Producer/Consumer
# =============================================================================


def example_1_basic_producer_consumer():
    """
    Example 1: Basic message production and consumption.

    Demonstrates:
    - Creating a producer
    - Sending messages
    - Creating a consumer
    - Consuming messages
    """
    print("\n" + "=" * 80)
    print("Example 1: Basic Producer/Consumer")
    print("=" * 80)

    # Configure Kafka
    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="example-topic",
        group_id="example-group",
    )

    # Produce messages
    print("\nProducing messages...")
    with StreamProducerFactory.create(settings) as producer:
        for i in range(5):
            message = f"Message {i}: Hello from axiompy!"
            result = producer.send(message, key=f"msg-{i}")
            print(f"  Sent: {message} (offset: {result.offset})")

    # Consume messages
    print("\nConsuming messages...")
    with StreamConsumerFactory.create(settings) as consumer:
        for message in consumer.consume(max_messages=5, timeout_seconds=10):
            print(f"  Received: {message.value.decode('utf-8')} (key: {message.key})")
            consumer.commit(message)


# =============================================================================
# Example 2: DataFrame Integration
# =============================================================================


def example_2_dataframe_integration():
    """
    Example 2: Send and receive DataFrames via streaming.

    Demonstrates:
    - Sending DataFrame rows as messages
    - Consuming messages back into DataFrame
    - JSON serialization
    """
    print("\n" + "=" * 80)
    print("Example 2: DataFrame Integration")
    print("=" * 80)

    # Create sample DataFrame
    df = pd.DataFrame(
        {
            "user_id": [1, 2, 3, 4, 5],
            "action": ["login", "purchase", "view", "purchase", "logout"],
            "amount": [0.0, 99.99, 0.0, 149.99, 0.0],
            "timestamp": pd.date_range("2024-01-01", periods=5),
        }
    )

    print("\nOriginal DataFrame:")
    print(df)

    # Send DataFrame to stream
    settings = StreamSettings(
        engine=StreamEngine.KAFKA, bootstrap_servers=["localhost:9092"], topic="df-example"
    )

    print("\nSending DataFrame to stream...")
    with StreamProducerFactory.create(settings) as producer:
        results = producer.send_dataframe(df, key_column="user_id", format="json")
        print(f"  Sent {len(results)} rows to stream")

    # Consume back to DataFrame
    settings.group_id = "df-consumer"
    print("\nConsuming back to DataFrame...")
    with StreamConsumerFactory.create(settings) as consumer:
        consumed_df = consumer.consume_to_dataframe(
            max_messages=10, timeout_seconds=5, parse_json=True
        )
        print(consumed_df)


# =============================================================================
# Example 3: Real-Time ETL Pipeline
# =============================================================================


def example_3_realtime_etl():
    """
    Example 3: Real-time ETL pipeline.

    Demonstrates:
    - Reading from input stream
    - Transforming data
    - Writing to output stream
    - Data quality monitoring
    """
    print("\n" + "=" * 80)
    print("Example 3: Real-Time ETL Pipeline")
    print("=" * 80)

    # Input stream (raw events)
    input_settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="raw-events",
        group_id="etl-processor",
    )

    # Output stream (clean events)
    output_settings = StreamSettings(
        engine=StreamEngine.KAFKA, bootstrap_servers=["localhost:9092"], topic="clean-events"
    )

    # Produce sample raw events
    print("\nProducing raw events...")
    with StreamProducerFactory.create(input_settings) as producer:
        raw_events = [
            {"user_id": 1, "score": 85, "age": None},
            {"user_id": 2, "score": None, "age": 30},
            {"user_id": 3, "score": 92, "age": 25},
            {"user_id": 4, "score": 78, "age": None},
            {"user_id": 5, "score": 95, "age": 28},
        ]

        for event in raw_events:
            producer.send(json.dumps(event), key=str(event["user_id"]))
        print(f"  Produced {len(raw_events)} raw events")

    # Consume, transform, and produce
    print("\nProcessing ETL pipeline...")
    with StreamConsumerFactory.create(input_settings) as consumer:
        # Consume to DataFrame
        df = consumer.consume_to_dataframe(max_messages=10, parse_json=True)
        print(f"\n  Consumed {len(df)} events")
        print(df)

        # Profile data quality
        profiler = DataProfilerFactory.create_auto(df)
        report = profiler.profile(df)
        print(f"\n  Quality Issues: {len(report.issues)}")
        print(f"  Null counts: {report.null_counts}")

        # Transform data
        transformer = DataTransformerFactory.create_auto(df)
        clean_df = transformer.fill_nulls(df, strategy="mean", columns=["score", "age"])
        print("\n  After transformation:")
        print(clean_df)

        # Send to output stream
        with StreamProducerFactory.create(output_settings) as producer:
            results = producer.send_dataframe(clean_df, key_column="user_id")
            print(f"\n  Sent {len(results)} clean events to output stream")


# =============================================================================
# Example 4: Data Sink Pattern
# =============================================================================


def example_4_data_sink():
    """
    Example 4: Consumer as data sink.

    Demonstrates:
    - Handler function pattern
    - Processing messages with custom logic
    - Statistics tracking
    - Error handling
    """
    print("\n" + "=" * 80)
    print("Example 4: Data Sink Pattern")
    print("=" * 80)

    # Produce sample messages
    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="sink-example",
        group_id="sink-consumer",
    )

    print("\nProducing messages...")
    with StreamProducerFactory.create(settings) as producer:
        events = [
            {"event_id": i, "type": "click" if i % 2 == 0 else "view", "value": i * 10}
            for i in range(10)
        ]
        for event in events:
            producer.send(json.dumps(event), key=str(event["event_id"]))
        print(f"  Produced {len(events)} events")

    # Define sink handler
    processed_events = []

    def process_event(message):
        """Handler function - processes each event."""
        event = json.loads(message.value.decode("utf-8"))

        # Custom processing logic
        processed = {
            **event,
            "processed_at": datetime.now().isoformat(),
            "doubled_value": event["value"] * 2,
        }

        processed_events.append(processed)
        logger.info(f"Processed event {event['event_id']}")

    # Consume with handler (sink pattern)
    print("\nProcessing events with sink pattern...")
    with StreamConsumerFactory.create(settings) as consumer:
        stats = consumer.consume_with_handler(
            handler=process_event, max_messages=10, timeout_seconds=10, fail_fast=False
        )

        print("\nStatistics:")
        print(f"  Messages consumed: {stats.messages_consumed}")
        print(f"  Messages processed: {stats.messages_processed}")
        print(f"  Messages failed: {stats.messages_failed}")
        print(f"  Throughput: {stats.throughput_msg_per_sec:.1f} msg/sec")
        print(f"  Total bytes: {stats.bytes_consumed} bytes")

        print(f"\nProcessed {len(processed_events)} events:")
        for event in processed_events[:3]:
            print(f"  {event}")


# =============================================================================
# Example 5: Multi-Platform Integration
# =============================================================================


def example_5_multi_platform():
    """
    Example 5: Reading from one platform, writing to another.

    Demonstrates:
    - Cross-platform streaming
    - Kafka -> Kinesis
    - Message transformation
    """
    print("\n" + "=" * 80)
    print("Example 5: Multi-Platform Integration (Kafka -> Kinesis)")
    print("=" * 80)

    # Kafka input
    kafka_settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="kafka-input",
        group_id="multi-platform",
    )

    # Kinesis output (requires AWS credentials)
    kinesis_settings = StreamSettings(
        engine=StreamEngine.KINESIS, topic="kinesis-output", region="us-east-1"
    )

    # Produce to Kafka
    print("\nProducing to Kafka...")
    with StreamProducerFactory.create(kafka_settings) as producer:
        for i in range(5):
            event = {"id": i, "platform": "kafka", "timestamp": datetime.now().isoformat()}
            producer.send(json.dumps(event), key=str(i))
        print("  Produced 5 events to Kafka")

    # Note: Kinesis portion requires AWS setup
    print("\nNote: Kinesis integration requires AWS credentials")
    print("To use Kinesis:")
    print("  1. Configure AWS credentials")
    print("  2. Create Kinesis stream")
    print("  3. Update kinesis_settings with your stream name")


# =============================================================================
# Example 6: Batch Processing with Streaming
# =============================================================================


def example_6_batch_streaming():
    """
    Example 6: Combine batch processing with streaming.

    Demonstrates:
    - Batch consumption
    - Batch transformation
    - Batch production
    - High throughput
    """
    print("\n" + "=" * 80)
    print("Example 6: Batch Processing with Streaming")
    print("=" * 80)

    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="batch-example",
        group_id="batch-consumer",
        batch_size=100,  # Process 100 messages at a time
    )

    # Produce large batch
    print("\nProducing batch of 100 messages...")
    with StreamProducerFactory.create(settings) as producer:
        messages = [f"Batch message {i}" for i in range(100)]
        keys = [f"key-{i}" for i in range(100)]
        results = producer.send_batch(messages, keys=keys)
        print(f"  Sent {len(results)} messages in batch")
        print(f"  Success rate: {sum(r.success for r in results) / len(results) * 100:.1f}%")

    # Consume in batches
    print("\nConsuming in batches...")
    with StreamConsumerFactory.create(settings) as consumer:
        batch_count = 0
        total_messages = 0

        while total_messages < 100:
            batch = consumer.consume_batch(batch_size=20, timeout_seconds=5)
            if not batch:
                break

            batch_count += 1
            total_messages += len(batch)
            print(f"  Batch {batch_count}: {len(batch)} messages")

            # Commit entire batch
            consumer.commit()

        stats = consumer.get_stats()
        print(f"\nTotal consumed: {stats.messages_consumed} messages")
        print(f"Throughput: {stats.throughput_msg_per_sec:.1f} msg/sec")


# =============================================================================
# Example 7: Stream Monitoring and Alerting
# =============================================================================


def example_7_monitoring():
    """
    Example 7: Monitor stream quality and alert on issues.

    Demonstrates:
    - Real-time data quality monitoring
    - Alert generation
    - Statistics tracking
    """
    print("\n" + "=" * 80)
    print("Example 7: Stream Monitoring and Alerting")
    print("=" * 80)

    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="monitoring-example",
        group_id="monitor",
    )

    # Produce messages with quality issues
    print("\nProducing messages with quality issues...")
    with StreamProducerFactory.create(settings) as producer:
        messages = [
            {"id": 1, "value": 100, "status": "valid"},
            {"id": 2, "value": None, "status": "valid"},  # Missing value
            {"id": 3, "value": -50, "status": "valid"},  # Negative value
            {"id": 4, "value": 200, "status": "valid"},
            {"id": 5, "value": None, "status": None},  # Multiple issues
        ]

        for msg in messages:
            producer.send(json.dumps(msg), key=str(msg["id"]))
        print(f"  Produced {len(messages)} messages")

    # Monitor stream
    print("\nMonitoring stream quality...")
    with StreamConsumerFactory.create(settings) as consumer:
        df = consumer.consume_to_dataframe(max_messages=10, parse_json=True)

        # Profile data
        profiler = DataProfilerFactory.create_auto(df)
        report = profiler.profile(df)

        print("\nQuality Report:")
        print(f"  Total rows: {report.row_count}")
        print(f"  Null counts: {report.null_counts}")
        print(f"  Issues found: {len(report.issues)}")

        # Check for alerts
        alerts = []
        if report.null_counts.get("value", 0) > 0:
            alerts.append("⚠️  NULL values detected in 'value' column")

        for col, stats in report.statistics.items():
            if col == "value" and stats.get("min", 0) < 0:
                alerts.append("⚠️  Negative values detected in 'value' column")

        if alerts:
            print("\n🚨 ALERTS:")
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("\n✅ No quality issues detected")


# =============================================================================
# Example 8: Stream Handler Pattern
# =============================================================================


def example_8_stream_handler():
    """
    Example 8: Using StreamHandler for composable message processing.

    Demonstrates:
    - Creating custom StreamHandler implementations
    - Separation of deserialization and processing logic
    - Type-safe message handling
    - Handler reusability
    """
    print("\n" + "=" * 80)
    print("Example 8: Stream Handler Pattern")
    print("=" * 80)

    # Define domain model
    @dataclass
    class UserEvent:
        user_id: int
        action: str
        timestamp: str
        amount: float = 0.0

    # Create JSON handler for UserEvents
    class JsonUserEventHandler(StreamHandler[UserEvent]):
        """Handler that deserializes JSON messages to UserEvent objects."""

        def deserialize(self, message: StreamMessage) -> Optional[UserEvent]:
            """Deserialize JSON message to UserEvent."""
            try:
                data = json.loads(message.value.decode("utf-8"))
                return UserEvent(
                    user_id=data["user_id"],
                    action=data["action"],
                    timestamp=data.get("timestamp", datetime.now().isoformat()),
                    amount=data.get("amount", 0.0),
                )
            except Exception as e:
                logger.error(f"Failed to deserialize message: {e}")
                return None

        def handle(self, event: UserEvent) -> None:
            """Process the deserialized event."""
            # Log event
            logger.info(
                f"User {event.user_id} performed {event.action} (amount: ${event.amount:.2f})"
            )

            # Business logic based on event type
            if event.action == "purchase" and event.amount > 100:
                logger.warning(f"High-value purchase detected: ${event.amount:.2f}")

    # Produce sample events
    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="user-events",
        group_id="handler-example",
    )

    print("\nProducing user events...")
    with StreamProducerFactory.create(settings) as producer:
        events = [
            {"user_id": 1, "action": "login", "amount": 0.0},
            {"user_id": 2, "action": "purchase", "amount": 49.99},
            {"user_id": 3, "action": "purchase", "amount": 199.99},
            {"user_id": 1, "action": "logout", "amount": 0.0},
        ]

        for event in events:
            event["timestamp"] = datetime.now().isoformat()
            producer.send(json.dumps(event), key=str(event["user_id"]))
        print(f"  Produced {len(events)} events")

    # Consume with StreamHandler
    print("\nConsuming with StreamHandler...")
    handler = JsonUserEventHandler()

    with StreamConsumerFactory.create(settings) as consumer:
        for message in consumer.consume(max_messages=10, timeout_seconds=5):
            # Use handler to process message
            if handler.process_message(message):
                consumer.commit(message)
                print(f"  ✓ Processed message {message.key}")
            else:
                print(f"  ✗ Failed to process message {message.key}")

    print("\nBenefits of StreamHandler:")
    print("  • Separates deserialization from processing logic")
    print("  • Type-safe with generic support")
    print("  • Easy to test deserializers and handlers independently")
    print("  • Reusable across different consumers")
    print("  • Swap serialization formats without changing business logic")


# =============================================================================
# Example 9: Multiple Handlers for Different Message Types
# =============================================================================


def example_9_multiple_handlers():
    """
    Example 9: Using multiple handlers for different message types.

    Demonstrates:
    - Routing messages to different handlers
    - Handler composition
    - Multi-format support
    """
    print("\n" + "=" * 80)
    print("Example 9: Multiple Handlers")
    print("=" * 80)

    # Define different event types
    @dataclass
    class LoginEvent:
        user_id: int
        ip_address: str

    @dataclass
    class PurchaseEvent:
        user_id: int
        product_id: int
        amount: float

    # Create handlers for each type
    class LoginEventHandler(StreamHandler[LoginEvent]):
        def deserialize(self, message: StreamMessage) -> Optional[LoginEvent]:
            try:
                data = json.loads(message.value.decode("utf-8"))
                return LoginEvent(user_id=data["user_id"], ip_address=data["ip_address"])
            except Exception:
                return None

        def handle(self, event: LoginEvent) -> None:
            logger.info(f"Login detected: User {event.user_id} from {event.ip_address}")

    class PurchaseEventHandler(StreamHandler[PurchaseEvent]):
        def deserialize(self, message: StreamMessage) -> Optional[PurchaseEvent]:
            try:
                data = json.loads(message.value.decode("utf-8"))
                return PurchaseEvent(
                    user_id=data["user_id"], product_id=data["product_id"], amount=data["amount"]
                )
            except Exception:
                return None

        def handle(self, event: PurchaseEvent) -> None:
            logger.info(
                f"Purchase: User {event.user_id} bought product {event.product_id} "
                f"for ${event.amount:.2f}"
            )

    # Message router
    def route_message(message: StreamMessage) -> bool:
        """Route message to appropriate handler based on headers."""
        event_type = message.headers.get("event_type", "")

        if event_type == "login":
            return login_handler.process_message(message)
        elif event_type == "purchase":
            return purchase_handler.process_message(message)
        else:
            logger.warning(f"Unknown event type: {event_type}")
            return False

    # Create handlers
    login_handler = LoginEventHandler()
    purchase_handler = PurchaseEventHandler()

    # Produce different event types
    settings = StreamSettings(
        engine=StreamEngine.KAFKA,
        bootstrap_servers=["localhost:9092"],
        topic="multi-events",
        group_id="multi-handler",
    )

    print("\nProducing mixed event types...")
    with StreamProducerFactory.create(settings) as producer:
        # Login event
        producer.send(
            json.dumps({"user_id": 1, "ip_address": "192.168.1.1"}),
            key="user-1",
            headers={"event_type": "login"},
        )

        # Purchase event
        producer.send(
            json.dumps({"user_id": 1, "product_id": 42, "amount": 99.99}),
            key="user-1",
            headers={"event_type": "purchase"},
        )

        print("  Produced login and purchase events")

    # Consume with routing
    print("\nConsuming with message routing...")
    with StreamConsumerFactory.create(settings) as consumer:
        for message in consumer.consume(max_messages=5, timeout_seconds=5):
            if route_message(message):
                consumer.commit(message)
                print(f"  ✓ Routed and processed {message.headers.get('event_type')}")


# =============================================================================
# Example 10: Context Managers and Resource Management
# =============================================================================


def example_10_resource_management():
    """
    Example 10: Proper resource management with context managers.

    Demonstrates:
    - Using context managers
    - Automatic cleanup
    - Error handling
    """
    print("\n" + "=" * 80)
    print("Example 10: Resource Management")
    print("=" * 80)

    settings = StreamSettings(
        engine=StreamEngine.KAFKA, bootstrap_servers=["localhost:9092"], topic="resource-example"
    )

    # With context manager (recommended)
    print("\nUsing context manager (automatic cleanup):")
    with StreamProducerFactory.create(settings) as producer:
        result = producer.send("Message with auto-cleanup")
        print(f"  Sent: {result.success}")
    print("  Producer automatically closed")

    # Manual management (not recommended)
    print("\nManual management:")
    producer = StreamProducerFactory.create(settings)
    try:
        result = producer.send("Message with manual cleanup")
        print(f"  Sent: {result.success}")
    finally:
        producer.close()
        print("  Producer manually closed")

    # Error handling
    print("\nWith error handling:")
    try:
        with StreamProducerFactory.create(settings) as producer:
            producer.send("Safe message")
            # Simulate error
            # raise Exception("Something went wrong")
    except Exception as e:
        print(f"  Error: {e}")
        print("  Resources still cleaned up properly")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("AxiomPy Streaming Examples")
    print("=" * 80)
    print("\nNOTE: These examples require running streaming services:")
    print("  - Kafka: docker run -p 9092:9092 apache/kafka")
    print("  - Kinesis: AWS account with credentials")
    print("  - Redis: docker run -p 6379:6379 redis")
    print("  - RabbitMQ: docker run -p 5672:5672 rabbitmq")
    print("\nFor local testing, install and run Kafka:")
    print("  docker-compose up kafka  # if you have docker-compose.yml")
    print("=" * 80)

    # Run examples (comment out as needed)
    try:
        example_1_basic_producer_consumer()
        # example_2_dataframe_integration()
        # example_3_realtime_etl()
        # example_4_data_sink()
        # example_5_multi_platform()
        # example_6_batch_streaming()
        # example_7_monitoring()
        # example_8_stream_handler()
        # example_9_multiple_handlers()
        # example_10_resource_management()
    except Exception as e:
        print(f"\n⚠️  Error running examples: {e}")
        print("Make sure streaming services are running and accessible")
