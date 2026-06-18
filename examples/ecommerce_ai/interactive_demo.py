# @!documentation

#!/usr/bin/env python3
"""
🛍️  Interactive E-Commerce Data Intelligence Demo

Demonstrates the complete AI reasoning pipeline:
1. 💬 User enters natural language question
2. 🧠 Agent analyzes question
3. ⚙️  Agent generates SQL
4. 📊 Data is retrieved from database
5. 💡 AI generates insights
6. ✨ Formatted response displayed

Requirements:
- Run `python setup.py` first to initialize database
- Ollama running for LLM features (optional)
"""

import logging
import sys
import time
from pathlib import Path
from typing import Any

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from axiompy.reasoning import ReasoningFactory
from axiompy.reasoning.agents import QueryAgent
from ecommerce.config.settings import (
    AI_MODEL,
    AI_PROVIDER,
    DATABASE_PATH,
    ENABLE_INSIGHTS,
    ENABLE_PLANNING,
)
from ecommerce.services.ecommerce_service import EcommerceService

from axiompy.io.database import DatabaseFactory, DatabaseSettings, DatabaseType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger("axiompy.io.database").setLevel(logging.WARNING)


# ANSI color codes for pretty output
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def print_header(text: str):
    """Print a fancy header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")


def print_section(emoji: str, title: str):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{emoji} {title}{Colors.END}")
    print(f"{Colors.DIM}{'─' * 80}{Colors.END}")


def print_step(step_num: int, description: str):
    """Print a pipeline step."""
    print(f"\n{Colors.BOLD}{Colors.YELLOW}Step {step_num}: {description}{Colors.END}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.END} {text}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}→{Colors.END} {text}")


def print_data(label: str, value: Any, indent: int = 2):
    """Print labeled data."""
    spaces = " " * indent
    print(f"{spaces}{Colors.DIM}{label}:{Colors.END} {Colors.BOLD}{value}{Colors.END}")


def animate_thinking(duration: float = 1.0):
    """Show a thinking animation."""
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    end_time = time.time() + duration
    i = 0
    while time.time() < end_time:
        print(
            f"\r{Colors.CYAN}{frames[i % len(frames)]}{Colors.END} Analyzing...", end="", flush=True
        )
        time.sleep(0.1)
        i += 1
    print(f"\r{' ' * 20}\r", end="")


class InteractiveDemo:
    """Interactive E-Commerce AI demo with full reasoning pipeline."""

    def __init__(self):
        """Initialize the demo."""
        self.service = None
        self.agent = None
        self.setup_complete = False
        self.ai_available = False

    def setup(self):
        """Set up services and agent."""
        print_section("🔧", "Initializing Services")

        # Check database
        if not DATABASE_PATH.exists():
            print(f"\n{Colors.RED}❌ Error: Database not found!{Colors.END}")
            print(f"\n{Colors.YELLOW}Please run:{Colors.END} python setup.py")
            return False

        print_success("Database file found")

        # Create database connection
        db_settings = DatabaseSettings(database=str(DATABASE_PATH))
        db = DatabaseFactory.create(DatabaseType.SQLITE, db_settings)
        self.service = EcommerceService(db)

        print_success("Service initialized")

        # Create AI client
        try:
            if AI_PROVIDER == "ollama":
                ai = ReasoningFactory.create_ollama(model=AI_MODEL)
            elif AI_PROVIDER == "openai":
                ai = ReasoningFactory.create_openai(model=AI_MODEL)
            elif AI_PROVIDER == "anthropic":
                ai = ReasoningFactory.create_anthropic(model=AI_MODEL)
            else:
                ai = None

            self.agent = QueryAgent(
                ai_client=ai if ai else ReasoningFactory.create_ollama(),
                datasets={"ecommerce": self.service},
                enable_planning=ENABLE_PLANNING,
                enable_insights=ENABLE_INSIGHTS and bool(ai),
                max_retries=2,
            )
            self.ai_available = bool(ai)
            print_success(f"AI Agent ready (LLM: {'enabled' if self.ai_available else 'disabled'})")
        except Exception as e:
            error_msg = str(e)
            print_info(f"AI not available: {error_msg}")

            # Provide helpful suggestions
            if "model" in error_msg.lower() and "not found" in error_msg.lower():
                print(f"\n{Colors.YELLOW}💡 Model not found. To fix:{Colors.END}")
                if AI_PROVIDER == "ollama":
                    print("   1. Install Ollama: https://ollama.ai")
                    print(f"   2. Pull a model: {Colors.CYAN}ollama pull llama2{Colors.END}")
                    print(f"   3. Start server: {Colors.CYAN}ollama serve{Colors.END}")
                    print("   4. Or edit config/settings.py to use OpenAI/Anthropic\n")
                elif AI_PROVIDER == "openai":
                    print(
                        f"   1. Set API key: {Colors.CYAN}export OPENAI_API_KEY='sk-...'{Colors.END}"
                    )
                    print("   2. Or install Ollama: https://ollama.ai\n")
                elif AI_PROVIDER == "anthropic":
                    print(
                        f"   1. Set API key: {Colors.CYAN}export ANTHROPIC_API_KEY='sk-ant-...'{Colors.END}"
                    )
                    print("   2. Or install Ollama: https://ollama.ai\n")
            elif "connection" in error_msg.lower() or "refused" in error_msg.lower():
                print(f"\n{Colors.YELLOW}💡 Connection failed. To fix:{Colors.END}")
                print(f"   1. Start Ollama: {Colors.CYAN}ollama serve{Colors.END}")
                print("   2. Or switch to OpenAI/Anthropic in config/settings.py\n")

            print(
                f"   Proceeding with {Colors.CYAN}direct SQL queries{Colors.END} (no AI insights)"
            )
            self.ai_available = False
            self.agent = None

        print_info(f"Capabilities: {', '.join(self.service.get_capabilities()[:3])}...")

        self.setup_complete = True
        return True

    def process_query(self, question: str) -> dict[str, Any]:
        """
        Process a query through the complete pipeline.

        Pipeline:
        1. Agent analyzes question
        2. Creates execution plan
        3. Generates SQL
        4. Executes query
        5. Generates insights
        """
        print_header("🤖 AI REASONING PIPELINE")

        # Display the question
        print(f'{Colors.BOLD}Question:{Colors.END} {Colors.CYAN}"{question}"{Colors.END}\n')

        # Step 1: Analysis
        print_step(1, "Agent Analyzes Question")
        animate_thinking(0.5)
        print_info("Parsing natural language...")
        print_info("Identifying intent and entities...")

        # Step 2: SQL Generation
        print_step(2, "Generating SQL Query")
        animate_thinking(0.5)

        # Step 3: Execution
        try:
            result = self.agent.execute_query(question)

            # DEBUG: Show full SQL immediately
            if result.get("sql"):
                print(f"\n{Colors.BOLD}Generated SQL (Full):{Colors.END}")
                print(f"{Colors.DIM}{result['sql']}{Colors.END}\n")

            if result.get("error"):
                print(f"\n{Colors.RED}❌ Error: {result['error']}{Colors.END}")
                return result

            print_success("Query executed successfully")

        except Exception as e:
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")
            return {"error": str(e)}

        # Step 4: Data Retrieval
        print_step(3, "Retrieving Data")
        results = result.get("results", [])
        result_count = len(results)

        print_success(f"Retrieved {result_count} records")

        # Show generated SQL
        if result.get("sql"):
            print_data(
                "Generated SQL",
                result["sql"][:60] + "..." if len(result["sql"]) > 60 else result["sql"],
            )

        # Show sample data
        if results and len(results) > 0:
            print(f"\n  {Colors.BOLD}Sample Results:{Colors.END}")
            for i, row in enumerate(results[:3], 1):
                fields = list(row.items())[:3]
                field_str = ", ".join(f"{Colors.CYAN}{k}{Colors.END}={v}" for k, v in fields)
                print(f"  {i}. {field_str}")
            if len(results) > 3:
                print(f"  {Colors.DIM}... and {len(results) - 3} more{Colors.END}")

        # Step 5: Insight Generation
        print_step(4, "Generating AI Insights")
        animate_thinking(1.0)

        insight = result.get("insights", "")
        if insight:
            print_success("Insights generated")
        else:
            print_info("No insights available (LLM may be disabled)")

        return result

    def display_insights(self, result: dict[str, Any]):
        """Display the final insights in a pretty format."""
        print_section("💡", "AI INSIGHTS")

        insights = result.get("insights", "")
        if insights:
            # Split insights into lines and format
            lines = insights.split("\n")
            for line in lines:
                if line.strip():
                    # Detect bullet points or numbered lists
                    if line.strip().startswith(("-", "*", "•")):
                        print(f"  {Colors.GREEN}•{Colors.END} {line.strip()[1:].strip()}")
                    elif line.strip()[0].isdigit() and "." in line[:3]:
                        num = line.strip().split(".")[0]
                        text = line.strip().split(".", 1)[1].strip()
                        print(f"  {Colors.CYAN}{num}.{Colors.END} {text}")
                    else:
                        print(f"  {line.strip()}")
        else:
            print(f"{Colors.DIM}No AI insights generated (LLM disabled or unavailable){Colors.END}")

        # Show data summary
        result_count = len(result.get("results", []))
        print(f"\n{Colors.DIM}Based on analysis of {result_count} records{Colors.END}")

    def show_examples(self):
        """Show example questions."""
        print_section("💡", "Example Questions")

        examples = [
            (
                "Sales Analysis",
                [
                    "What are the top 5 product categories by revenue?",
                    "Which products have the most delivered orders?",
                    "Show me revenue by customer tier",
                ],
            ),
            (
                "Customer Analysis",
                [
                    "How many customers do we have in each country?",
                    "What's the distribution of customer tiers?",
                    "Show me the top 10 customers by lifetime value",
                ],
            ),
            (
                "Order Analysis",
                [
                    "What is the average order value?",
                    "What percentage of orders are pending?",
                    "Which order status is most common?",
                ],
            ),
        ]

        for category, questions in examples:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{category}:{Colors.END}")
            for i, q in enumerate(questions, 1):
                print(f"  {Colors.DIM}{i}.{Colors.END} {q}")

    def run(self):
        """Run the interactive demo."""
        # Banner
        print_header("🛍️  E-Commerce AI Intelligence - Interactive Demo")
        print(f"{Colors.DIM}Complete AI Reasoning Pipeline Demonstration{Colors.END}")
        print(
            f"{Colors.DIM}Ask natural language questions and watch the AI work its magic!{Colors.END}\n"
        )

        # Setup
        if not self.setup():
            return 1

        # Show examples
        self.show_examples()

        # Main loop
        print(f"\n{Colors.BOLD}Ready to answer your questions!{Colors.END}")
        print(
            f"{Colors.DIM}Type 'examples' for more, 'help' for commands, 'quit' to exit{Colors.END}\n"
        )

        while True:
            try:
                # Get question
                question = input(f"{Colors.BOLD}{Colors.GREEN}Your question >{Colors.END} ").strip()

                if not question:
                    continue

                # Check commands
                if question.lower() in ["quit", "exit", "q"]:
                    print(f"\n{Colors.CYAN}👋 Thanks for trying the demo!{Colors.END}\n")
                    break

                if question.lower() == "examples":
                    self.show_examples()
                    continue

                if question.lower() == "help":
                    print(f"\n{Colors.BOLD}Commands:{Colors.END}")
                    print(f"  {Colors.CYAN}examples{Colors.END} - Show example questions")
                    print(f"  {Colors.CYAN}quit{Colors.END}     - Exit the demo")
                    print(f"  {Colors.CYAN}help{Colors.END}     - Show this help")
                    continue

                # Process the question
                if not self.agent:
                    print(f"\n{Colors.YELLOW}⚠️  AI agent not available.{Colors.END}")
                    print(
                        f"   Execute SQL directly with: {Colors.CYAN}SELECT * FROM orders LIMIT 10{Colors.END}\n"
                    )
                    continue

                try:
                    result = self.process_query(question)
                except Exception as e:
                    error_msg = str(e)
                    print(f"\n{Colors.RED}❌ Error: {error_msg}{Colors.END}")

                    # Provide helpful hints
                    if "aggregate" in error_msg.lower():
                        print(
                            f"\n{Colors.YELLOW}💡 Hint: Aggregate function errors usually mean missing GROUP BY{Colors.END}"
                        )
                        print("   Try asking: 'Show me total revenue by category'")
                    elif "no such table" in error_msg.lower():
                        print(
                            f"\n{Colors.YELLOW}💡 Hint: Invalid table name. Available tables: customers, products, orders{Colors.END}"
                        )

                    print()
                    continue

                # Display insights
                if not result.get("error"):
                    self.display_insights(result)

                # Separator
                print(f"\n{Colors.DIM}{'─' * 80}{Colors.END}")

            except KeyboardInterrupt:
                print(f"\n\n{Colors.CYAN}👋 Interrupted. Goodbye!{Colors.END}\n")
                break
            except Exception as e:
                print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.END}")
                import traceback

                print(f"\n{Colors.DIM}{traceback.format_exc()}{Colors.END}")

        return 0


def main():
    """Main entry point."""
    demo = InteractiveDemo()
    return demo.run()


if __name__ == "__main__":
    exit(main())
