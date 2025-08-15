# QAgent - Refactored for API Integration
(This document is likely outdated, always refer to the root readme for most up-to-date changes. )
This project has been refactored to use a class-based architecture that makes it easy to integrate into backend APIs. All Python files now contain classes that can be instantiated and called programmatically.

## Overview

The refactored codebase consists of several specialized classes, each handling a specific part of the test planning workflow:

1. **PRDExtractor** - Extracts structured information from PRD documents
2. **FigmaFrameParser** - Parses Figma designs and extracts interactive components
3. **FigmaSummarizer** - Generates natural language summaries from Figma data
4. **TestPlanGenerator** - Generates test plans from PRD context and Figma data
5. **DetailedTestGenerator** - Creates detailed test cases from high-level test plans
6. **MarkdownFormatter** - Converts JSON data to Markdown format

## Class Structure

### PRDExtractor (`prd_to_specs.py`)

```python
from prd_to_specs import PRDExtractor

# Initialize with optional API key
extractor = PRDExtractor(api_key="your_gemini_api_key")

# Extract PRD context from file
prd_context = extractor.extract_prd_from_file("path/to/prd.pdf")

# Save to file
extractor.save_prd_context(prd_context, "output/prd_context.json")
```

### FigmaFrameParser (`parse_figma_frame.py`)

```python
from parse_figma_frame import FigmaFrameParser

# Initialize with optional access token
parser = FigmaFrameParser(access_token="your_figma_token")

# Parse Figma design from URL
figma_data = parser.parse_figma_frame_from_url("https://www.figma.com/file/...")

# Save to file
parser.save_figma_data(figma_data, "output/figma_data.json")
```

### FigmaSummarizer (`summarize_figma_data.py`)

```python
from summarize_figma_data import FigmaSummarizer

# Initialize with optional API key
summarizer = FigmaSummarizer(api_key="your_gemini_api_key")

# Generate summary from Figma data
summary = summarizer.generate_figma_summary("figma_data.json")

# Save to file
summarizer.save_figma_summary(summary, "output/figma_summary.txt")
```

### TestPlanGenerator (`generate_test_plan.py`)

```python
from generate_test_plan import TestPlanGenerator

# Initialize with optional API key
generator = TestPlanGenerator(api_key="your_gemini_api_key")

# Generate test plan from files
test_plan = generator.generate_test_plan_from_files(
    context_path="prd_context.json",
    figma_path="figma_summary.txt"
)

# Save to file
generator.save_test_plan(test_plan, "output/test_plan.json")
```

### DetailedTestGenerator (`generate_detailed_tests.py`)

```python
from generate_detailed_tests import DetailedTestGenerator

# Initialize with optional API key
generator = DetailedTestGenerator(api_key="your_gemini_api_key")

# Generate detailed test suite
test_suite = generator.generate_detailed_test_suite(
    test_plan_path="test_plan.md",
    figma_summary_path="figma_summary.txt",
    max_test_cases=5
)

# Save to file
generator.save_test_suite(test_suite, "output/test_suite.json")
```

### MarkdownFormatter (`json_to_md_formatter.py`)

```python
from json_to_md_formatter import MarkdownFormatter

# Initialize formatter
formatter = MarkdownFormatter()

# Convert test plan to Markdown
formatter.convert_test_plan("test_plan.json", "output/test_plan.md")

# Convert test suite to Markdown
formatter.convert_test_suite("test_suite.json", "output/test_suite.md")
```

## Complete Workflow Example

The `api_example.py` file demonstrates how to use all classes together in a complete workflow:

```python
from api_example import TestPlanningAPI

# Initialize the main API class
api = TestPlanningAPI()

# Run the complete workflow
result = api.run_complete_workflow(
    prd_file_path="path/to/your/prd.pdf",
    figma_url="https://www.figma.com/file/your-file-key",
    output_dir="my_test_plan_output"
)

print("Workflow completed!")
print(f"Output files: {result['output_files']}")
```

## API Integration Examples

### Flask Integration

```python
from flask import Flask, request, jsonify
from api_example import TestPlanningAPI

app = Flask(__name__)
api = TestPlanningAPI()

@app.route('/generate-test-plan', methods=['POST'])
def generate_test_plan():
    data = request.get_json()
    test_plan = api.generate_test_plan(
        data['prd_context'], 
        data['figma_summary']
    )
    return jsonify(test_plan)

if __name__ == '__main__':
    app.run(debug=True)
```

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from api_example import TestPlanningAPI

app = FastAPI()
api = TestPlanningAPI()

class TestPlanRequest(BaseModel):
    prd_context: dict
    figma_summary: str

@app.post("/generate-test-plan")
async def generate_test_plan(request: TestPlanRequest):
    try:
        test_plan = api.generate_test_plan(
            request.prd_context, 
            request.figma_summary
        )
        return test_plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Environment Setup

Create a `.env` file with your API keys:

```env
GEMINI_API_KEY=your_gemini_api_key_here
FIGMA_ACCESS_TOKEN=your_figma_access_token_here
```

## Key Benefits of the Refactored Structure

1. **Modularity**: Each class has a single responsibility and can be used independently
2. **Reusability**: Classes can be instantiated multiple times with different configurations
3. **Testability**: Each class can be unit tested independently
4. **API Ready**: Classes are designed to be easily integrated into web frameworks
5. **Error Handling**: Proper exception handling and error messages
6. **Flexibility**: Optional parameters allow for different initialization patterns
7. **Backward Compatibility**: CLI interfaces are preserved for existing workflows

## CLI Usage (Still Available)

All original CLI functionality is preserved. You can still use the scripts from the command line:

```bash
# Extract PRD context
python prd_to_specs.py path/to/prd.pdf

# Parse Figma design
python parse_figma_frame.py "https://www.figma.com/file/..."

# Generate test plan
python generate_test_plan.py

# Generate detailed tests
python generate_detailed_tests.py

# Convert to Markdown
python json_to_md_formatter.py --type test_plan --json_path test_plan.json
```

## Error Handling

All classes include proper error handling:

- **FileNotFoundError**: When input files don't exist
- **ValueError**: When required parameters are missing or invalid
- **API Exceptions**: When external API calls fail
- **IOError**: When file operations fail

## Dependencies

The refactored code maintains the same dependencies as the original:

```
google-generativeai
pydantic
python-dotenv
PyPDF2
PyYAML
requests
```

## Migration Guide

If you're migrating from the old script-based approach:

1. **Replace function calls** with class instantiation and method calls
2. **Update imports** to import the classes instead of functions
3. **Handle exceptions** using try-catch blocks around class methods
4. **Use the TestPlanningAPI class** for complete workflow orchestration

## Contributing

When adding new functionality:

1. Create a new class or extend existing classes
2. Add proper type hints and docstrings
3. Include error handling
4. Maintain backward compatibility with CLI interfaces
5. Add unit tests for new functionality

## Support

For questions or issues with the refactored code, please refer to the individual class docstrings or the `api_example.py` file for usage examples. 