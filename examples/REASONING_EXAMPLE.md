# AxiomPy Reasoning Example

A complete, self-contained example demonstrating AxiomPy's AI-powered reasoning capabilities.

## What This Example Shows

This example demonstrates the core concepts of AxiomPy's reasoning module:

1. **BaseDatasetService** - Creating dataset services with standard interface
2. **DatasetMetadata** - Defining rich metadata for AI reasoning
3. **AIClient** - Provider-agnostic LLM interface
4. **QueryAgent** - Intelligent query routing and execution
5. **SQLValidator** - SQL validation to prevent errors

## Features

✅ **No External Data Sources**
- Uses in-memory data for complete self-contained example
- Easy to swap with real databases using `axiompy.io.database`

✅ **Multiple Datasets**
- Sales data service
- Employee directory service
- Demonstrates intelligent routing between datasets

✅ **Provider-Agnostic**
- Works with Ollama (local, free)
- Compatible with OpenAI and Anthropic
- Same code works with any LLM

✅ **Production Patterns**
- Type-safe with full type hints
- Comprehensive error handling
- Real-world structured data

## Setup

### Prerequisites

1. **Python 3.10+**
2. **AxiomPy installed**
   ```bash
   cd /Users/JVaron/code/axiompy
   pip install -e .
   ```

### Option 1: Using Ollama (Recommended for Local Development)

1. **Install Ollama**
   ```bash
   # Visit https://ollama.ai and download
   # Or: brew install ollama (macOS)
   ```

2. **Start Ollama server**
   ```bash
   ollama serve
   ```
   (runs on `http://localhost:11434`)

3. **Pull a model**
   ```bash
   ollama pull mistral  # or: ollama pull llama2, neural-chat, etc.
   ```

### Option 2: Using OpenAI

1. **Get API key**
   - Visit https://platform.openai.com/api/keys
   - Create new secret key

2. **Edit the example**
   ```python
   # In main() function, replace:
   ai_client = ReasoningFactory.create(ReasoningProvider.OLLAMA(model="mistral")
   
   # With:
   ai_client = ReasoningFactory.create_openai(
       api_key="sk-your-key-here",
       model="gpt-4"
   )
   ```

### Option 3: Using Anthropic

1. **Get API key**
   - Visit https://console.anthropic.com
   - Create new API key

2. **Edit the example**
   ```python
   # In main() function, replace:
   ai_client = ReasoningFactory.create(ReasoningProvider.OLLAMA(model="mistral")
   
   # With:
   ai_client = ReasoningFactory.create_anthropic(
       api_key="sk-ant-your-key-here",
       model="claude-3-opus-20240229"
   )
   ```

## Running the Example

```bash
cd /Users/JVaron/code/axiompy
python examples/reasoning_example.py
```

### Expected Output

```
================================================================================
AxiomPy Reasoning Example - AI-Powered Query Agent
================================================================================

Step 1: Creating dataset services...
  ✓ Sales service created
  ✓ Employee service created

Step 2: Creating AI client...
  Attempting to use local Ollama (make sure 'ollama serve' is running)...
  ✓ AI client created (Ollama)

Step 3: Creating query agent...
  ✓ Query agent created with 2 datasets

Step 4: Available datasets:
  • sales: regional_analysis, product_analysis, temporal_trends, sales_forecasting, revenue_analysis
  • employees: department_analysis, compensation_analysis, tenure_analysis, headcount_reporting, performance_metrics

Step 5: Executing natural language queries...

  Query 1: What are the sales by region?
    Dataset: sales
    Generated SQL: SELECT * FROM sales WHERE region = ...
    Results: 5 rows
    Sample: {'date': '2024-01', 'region': 'North', ...}
    Insights: Based on the sales data, the North region ...

  Query 2: How many employees are in engineering?
    Dataset: employees
    Generated SQL: SELECT * FROM employees WHERE department = ...
    Results: 2 rows
    Sample: {'emp_id': 1, 'name': 'Alice Johnson', ...}
    Insights: The engineering department currently has ...

  Query 3: Show me the sales data
    Dataset: sales
    Generated SQL: SELECT * FROM sales
    Results: 5 rows
    Sample: {'date': '2024-01', 'region': 'North', ...}
    Insights: The sales data shows ...

================================================================================
```

## Example Structure

### 1. Define Dataset Services

```python
class SalesDataService(BaseDatasetService):
    dataset_name = "sales"
    description = "E-commerce Sales Data"
    
    def query(self, sql: str, limit: int = None):
        # Implement query execution
        pass
    
    def get_capabilities(self):
        return ["regional_analysis", "product_analysis", ...]
    
    def get_metadata(self):
        return DatasetMetadata(...)
```

### 2. Create AI Client

```python
# Local - no API key needed
ai_client = ReasoningFactory.create(ReasoningProvider.OLLAMA(model="mistral")

# Or cloud-based
ai_client = ReasoningFactory.create_openai(api_key="sk-...", model="gpt-4")
```

### 3. Create Query Agent

```python
agent = QueryAgent(
    ai_client=ai_client,
    datasets={"sales": sales_service, "employees": employees_service}
)
```

### 4. Execute Queries

```python
result = agent.execute_query("What are the sales by region?")

# Result includes:
# - results: Query results from dataset
# - sql: Generated SQL query
# - dataset: Which dataset was used
# - insights: AI-generated insights from results
```

## Customization

### Adding More Datasets

```python
class YourDataService(BaseDatasetService):
    dataset_name = "your_dataset"
    description = "Your Dataset Description"
    
    # Implement required methods
    ...

# Add to agent
agent = QueryAgent(
    ai_client=ai_client,
    datasets={
        "sales": sales_service,
        "employees": employees_service,
        "your_dataset": YourDataService()
    }
)
```

### Using Real Databases

Replace in-memory data with `axiompy.io.database`:

```python
from axiompy.io.database import DatabaseFactory, DatabaseType

class RealDataService(BaseDatasetService):
    def __init__(self):
        self.db = DatabaseFactory.create(
            DatabaseType.SQLITE,
            {"database": "my_database.db"}
        )
    
    def query(self, sql: str, limit: int = None):
        return self.db.execute(sql, limit=limit)
```

### Configuring the Agent

```python
agent = QueryAgent(
    ai_client=ai_client,
    datasets=datasets,
    enable_planning=True,      # Use AI for dataset selection
    enable_insights=True,      # Generate insights from results
    max_retries=2              # Retry on SQL generation failure
)
```

## Key Concepts

### BaseDatasetService
- Abstract interface for dataset operations
- Enables AI agent integration
- Provides `query()`, `get_capabilities()`, `get_metadata()`
- Domain-agnostic (works with any data)

### DatasetMetadata
- Type-safe metadata definitions
- Includes schema, scope, capabilities, keywords
- Enables AI reasoning about data
- Used for intelligent routing and prompt generation

### AIClient
- Provider-agnostic LLM interface
- Methods: `generate_completion()`, `generate_sql_from_question()`, `generate_insight()`
- Built-in caching for performance
- Works with Ollama, OpenAI, Anthropic, or any HTTP-based AI service

### QueryAgent
- Orchestrates the query execution flow
- Routes questions to appropriate datasets
- Generates SQL from natural language
- Validates SQL before execution
- Generates insights from results

## Troubleshooting

### "Cannot connect to Ollama"

```
Error: Failed to connect to Ollama: ...
```

**Solution:**
1. Check Ollama is running: `ollama serve`
2. Verify model is installed: `ollama pull mistral`
3. Check endpoint: `http://localhost:11434`
4. Try alternative provider (OpenAI/Anthropic)

### "Invalid columns in generated SQL"

The QueryAgent validates SQL columns against schema. If you see validation errors:

1. Ensure your metadata defines all columns correctly
2. Check the generated SQL in the error message
3. The agent will retry automatically (configurable with `max_retries`)

### "No insights generated"

If the `insights` field is empty:
- Ensure `enable_insights=True` in QueryAgent
- Check your LLM is working with `generate_completion()`
- Try a simpler prompt

## Performance Notes

- **First query:** May take 5-10 seconds (LLM inference)
- **Subsequent queries:** Much faster due to caching
- **Dataset selection:** <50ms via keyword matching
- **SQL validation:** <10ms

To improve performance:
- Use faster LLM models (e.g., `neural-chat` vs `llama2`)
- Reduce `max_tokens` parameter
- Increase cache size in AIClient

## Next Steps

1. **Test with real data:**
   - Replace `SalesDataService.data` with database queries
   - Use `axiompy.io.database` for production databases

2. **Add more datasets:**
   - Create new `BaseDatasetService` subclasses
   - Add to agent with `QueryAgent(..., datasets={...})`

3. **Customize metadata:**
   - Define detailed schema with constraints
   - Add examples for few-shot learning
   - Include keywords for better routing

4. **Integrate with your app:**
   - Use `QueryAgent` in your API routes
   - Cache agent instance (don't recreate per request)
   - Handle errors appropriately

## Learn More

- **AxiomPy Reasoning Docs:** See `PHASE2_COMPLETE.md`
- **API Documentation:** Inline docstrings in `axiompy/reasoning/`
- **Examples:** See `examples/` directory

## Support

For issues or questions:
1. Check the inline comments in `reasoning_example.py`
2. Review `axiompy/reasoning/` module documentation
3. Check AxiomPy issue tracker

---

**Happy reasoning! 🚀**

