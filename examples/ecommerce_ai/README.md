# E-Commerce AI Intelligence System

**AxiomPy Reasoning Framework with 1 Million Records**

A production-ready example demonstrating AxiomPy's AI reasoning capabilities on realistic e-commerce data with 1M customer orders.

## Quick Start

### 1. Setup Database

Generate 1M synthetic records:

```bash
cd examples/ecommerce_ai
python setup.py
```

This creates `data/ecommerce.db` (~100MB) with:
- **100,000 customers** across 8 countries
- **500 products** in 7 categories
- **1,000,000 orders** spanning 12 months
- **$780M+ in total revenue**

Takes 2-5 minutes.

### 2. Run Demo

**Basic Demo:**
```bash
python main.py
```

**Interactive Demo (Recommended):**
```bash
python interactive_demo.py
```

Shows:
- ✅ AI-powered query routing
- ✅ Natural language to SQL conversion
- ✅ Automatic insights generation
- ✅ All AxiomPy reasoning components
- ✅ Real-time pipeline visualization (interactive only)
- ✅ Rich terminal UI with colors (interactive only)

## Project Structure

```
ecommerce_ai/
├── ecommerce/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Configuration
│   └── services/
│       ├── __init__.py
│       └── ecommerce_service.py # Main service
├── data/
│   └── ecommerce.db             # Generated database
├── tests/
│   ├── unit/                    # Unit tests
│   └── integration/             # Integration tests
├── setup.py                     # Database setup
├── main.py                      # Demo script
└── requirements.txt             # Dependencies
```

## Interactive Demo

The interactive demo provides a real-time visualization of the AI reasoning pipeline:

```
🤖 AI REASONING PIPELINE

Step 1: Agent Analyzes Question
   → Parsing natural language...
   → Identifying intent and entities...

Step 2: Generating SQL Query
   ⠹ Analyzing...

Step 3: Retrieving Data
   ✓ Retrieved 5 records

Step 4: Generating AI Insights
   ⠏ Analyzing...

💡 AI INSIGHTS
   • Top category is Electronics
   • Revenue dominated by Electronics and Clothing
```

**Features:**
- Colored output for easy reading
- Animated thinking indicators
- Step-by-step pipeline visualization
- Multiple example categories
- Real-time result display
- Natural language question support

**Usage:**
```bash
python interactive_demo.py
```

Then type questions like:
- `What are the top 5 product categories by revenue?`
- `How many customers do we have in each country?`
- `Show me revenue by customer tier`

Type `examples` to see more, `help` for commands, `quit` to exit.

## What's Inside

### EcommerceService

Implements `BaseDatasetService` interface:

```python
class EcommerceService(BaseDatasetService):
    def query(self, sql: str, limit: int = None) -> list[dict]:
        """Execute SQL queries"""

    def get_capabilities(self) -> list[str]:
        """List available analysis capabilities"""

    def get_metadata(self) -> DatasetMetadata:
        """Rich metadata for AI reasoning"""
```

### Database Schema

**customers** (100K rows)
- customer_id, name, email, country
- signup_date, customer_tier, lifetime_value

**products** (500 rows)
- product_id, name, category, price, stock

**orders** (1M rows)
- order_id, customer_id, product_id, order_date
- quantity, total_amount, status

### Configuration

Edit `ecommerce/config/settings.py`:

```python
# AI Provider
AI_PROVIDER = "ollama"  # "ollama", "openai", or "anthropic"
AI_MODEL = "mistral"

# Query Agent
ENABLE_PLANNING = True
ENABLE_INSIGHTS = True
```

## AI Provider Setup

### Option 1: Ollama (Recommended - No API Keys)

```bash
# Install Ollama: https://ollama.ai
ollama pull mistral
ollama serve
```

Then run demo (works offline):
```bash
python main.py
```

### Option 2: OpenAI

Edit `ecommerce/config/settings.py`:
```python
AI_PROVIDER = "openai"
AI_MODEL = "gpt-4"
```

Then set API key:
```bash
export OPENAI_API_KEY="sk-..."
python main.py
```

### Option 3: Anthropic

Edit `ecommerce/config/settings.py`:
```python
AI_PROVIDER = "anthropic"
AI_MODEL = "claude-3-opus"
```

Then set API key:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
python main.py
```

## Example Queries

Try modifying `main.py` to ask different questions:

```python
# Customer analysis
"How many customers do we have in each country?"
"What is the distribution of customer tiers?"
"Which customers have the highest lifetime value?"

# Product analysis
"What are the top 10 best-selling products?"
"Which categories have the highest average price?"

# Revenue analysis
"What is our total revenue by category?"
"What is the average order value?"

# Geographic analysis
"Where do we have the most customers?"
"Which country has the highest revenue?"
```

## AxiomPy Components Demonstrated

✅ **BaseDatasetService** - Service interface
✅ **DatasetMetadata** - Type-safe metadata schema
✅ **AIClient** - Provider-agnostic LLM interface
✅ **ReasoningFactory** - Easy client creation
✅ **QueryAgent** - Intelligent query routing
✅ **DynamicPromptBuilder** - Metadata-driven prompts
✅ **SQLValidator** - SQL safety validation
✅ **Large-scale data** - 1M records handling

## Architecture

```
User Question (Natural Language)
    ↓
QueryAgent (Planning + Routing)
    ↓
AIClient (SQL Generation)
    ├─ Ollama (local)
    ├─ OpenAI (cloud)
    └─ Anthropic (cloud)
    ↓
SQLValidator (Safety Check)
    ├─ Column validation
    ├─ Table validation
    └─ Syntax check
    ↓
Database Execution
    └─ SQLite (data/ecommerce.db)
    ↓
AIClient (Insight Generation)
    ↓
Results + SQL + Insights
```

## Performance

- **Data generation**: 2-5 minutes
- **Database size**: ~100MB
- **Query execution**: <1 second
- **AI response**: 2-5s (Ollama), 1-2s (cloud)
- **Total**: 3-6s from question to insights

## Customization

### Add More Data

In `setup.py`:
```python
generate_ecommerce_database(
    db_path=str(db_path),
    num_records=10_000_000  # 10M instead of 1M
)
```

### Create Custom Services

Use `EcommerceService` as template:

```python
from axiompy.reasoning import BaseDatasetService, DatasetMetadata
from axiompy.io.database import Database

class MyService(BaseDatasetService):
    dataset_name = "my_dataset"
    description = "My custom dataset"

    def __init__(self, db: Database):
        self.db = db

    def query(self, sql: str, limit: int = None):
        # Your implementation
        pass

    def get_capabilities(self):
        return ["analysis", "reporting"]

    def get_metadata(self):
        # Define metadata
        return DatasetMetadata(...)
```

### Run Tests

```bash
pytest tests/
pytest tests/unit/
pytest tests/integration/
```

## Troubleshooting

### Database not found
```bash
python setup.py
```

### Ollama not available
Install from https://ollama.ai and run `ollama serve`

### API key errors
Check environment variables are set correctly

### Memory issues
Generate fewer records:
```python
generate_ecommerce_database(num_records=100_000)
```

## Next Steps

1. **Explore** - Run the demo and examine generated SQL
2. **Customize** - Modify queries in `main.py`
3. **Extend** - Add more tables/data
4. **Integrate** - Use pattern in your projects
5. **Build** - Create your own AI-powered services

## Learning Path

```
1. Understand the structure
   └─ Read this README
   └─ Review ecommerce/config/settings.py
   └─ Check ecommerce/services/ecommerce_service.py

2. Run the demo
   └─ python setup.py (generate data)
   └─ python main.py (run demo)

3. Experiment
   └─ Try different questions
   └─ Modify settings.py
   └─ Test different AI providers

4. Customize
   └─ Add new metadata
   └─ Create new services
   └─ Write tests
```

## What This Example Shows

- **Production-ready pattern** for AI-powered data services
- **Best practices** from AxiomPy framework
- **Real-world scale** with 1M records
- **Multiple AI providers** (local and cloud)
- **SQL safety** via validation
- **Type-safe metadata** for AI reasoning

## Recommended Reading

1. `axiompy/reasoning/` - AI components
2. `axiompy/io/database.py` - Database abstraction
3. `examples/api_template/` - API patterns
4. AxiomPy README - Full framework overview

---

**Ready to build AI-powered data intelligence!** 🚀

---

**Last Updated:** 2025-12-03
