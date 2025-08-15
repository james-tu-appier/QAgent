import json
import argparse
import re
import time
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import yaml

# --- Pydantic Models for Structured Output from AI ---

class DetailedStep(BaseModel):
    """A single, granular step in a manual test case."""
    step_number: int = Field(..., description="The sequential number of the test step.")
    action: str = Field(..., description="The specific, single action the user should perform.")
    expected_result: str = Field(..., description="The precise, observable outcome of the action.")

class DetailedTestCaseResponse(BaseModel):
    """The expected JSON response from the AI for detailed test case generation."""
    detailed_steps: List[DetailedStep]

class DetailedTestGenerator:
    """Class for generating detailed test cases from high-level test plans."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the DetailedTestGenerator.
        
        Args:
            api_key: Gemini API key. If not provided, will try to load from environment.
        """
        if api_key is None:
            load_dotenv()
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
        
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
    
    def parse_md_table(self, md_content: str) -> List[Dict[str, Any]]:
        """Parses all high-level test case tables from a Markdown file."""
        all_test_cases = []
        # This regex is designed to be robust and find all test case tables in the document.
        table_pattern = re.compile(r"\| Test Case ID.*?\|\n\| :---.*?\|\n((?:\|.*?\|\n)+)", re.DOTALL)
        headers = ['Test Case ID', 'Test Scenario/Description', 'Test Steps', 'Expected Result', 'Rationale / Business Impact', 'Test Type', 'Priority']
        
        for match in table_pattern.finditer(md_content):
            rows_text = match.group(1).strip().split('\n')
            for row_text in rows_text:
                cells = [cell.strip().replace('`', '') for cell in row_text.split('|')][1:-1]
                if len(cells) == len(headers):
                    all_test_cases.append(dict(zip(headers, cells)))
        return all_test_cases

    def generate_detailed_steps(self, prompt_template: str, context: Dict) -> List[Dict[str, Any]]:
        """Calls the Gemini API to expand a high-level test case into detailed steps."""
        prompt = prompt_template.format(**context)
        
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            response_schema=DetailedTestCaseResponse,
        )

        max_retries = 3
        delay = 5 # seconds
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(contents=prompt, generation_config=generation_config)
                # Pydantic validates that the AI's JSON output matches the expected schema.
                parsed_response = DetailedTestCaseResponse.model_validate_json(response.text)
                return [step.model_dump() for step in parsed_response.detailed_steps]
            except (google_exceptions.ResourceExhausted, google_exceptions.DeadlineExceeded) as e:
                print(f"Warning: API limit/timeout for TC {context.get('test_case_id', 'N/A')}. Retrying in {delay}s... ({e})")
                time.sleep(delay)
                delay *= 2 # Exponential backoff
            except Exception as e:
                print(f"Error generating detailed steps for TC {context.get('test_case_id', 'N/A')}: {e}")
                # Return an empty list on failure to avoid stopping the entire process.
                return [] 
        return []

    def generate_bug_report_template(self, high_level_case: Dict[str, Any], detailed_steps: List[Dict[str, Any]]) -> str:
        """Creates a pre-formatted Markdown bug report using the generated detailed steps."""
        title = f"Bug: {high_level_case.get('Test Case ID', 'N/A')} - {high_level_case.get('Test Scenario/Description', 'No description')}"
        
        # Use the detailed, granular steps for reproducibility.
        steps_to_reproduce = "\n".join(f"{step['step_number']}. {step['action']}" for step in detailed_steps)
        
        # The final expected result is often the last step's outcome.
        final_expected_result = detailed_steps[-1]['expected_result'] if detailed_steps else "N/A"

        template = f"""
### {title}

**Priority:** {high_level_case.get('Priority', 'N/A')}
**Test Case:** `{high_level_case.get('Test Case ID', 'N/A')}`

---

#### Steps to Reproduce:
{steps_to_reproduce}

---

#### Expected Result:
{final_expected_result}

---

#### Actual Result:
*(QA to fill this in. Describe what actually happened when the test failed.)*

---

#### Notes / Environment:
- **Browser:** - **OS:** - **Notes:** *(QA to add any additional context, logs, or screenshots.)*
"""
        return template.strip()

    def load_prompt_from_yaml(self, file_path: str, key: str) -> str:
        """Loads a specific prompt template from a YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data[key]

    def generate_detailed_test_suite(self, 
                                   test_plan_path: str, 
                                   prompt_file_path: str = "prompt_templates/test_designer.yaml",
                                   figma_summary_path: Optional[str] = None,
                                   max_test_cases: int = 3) -> Dict[str, Any]:
        """
        Generate detailed test suite from a test plan.
        
        Args:
            test_plan_path: Path to the test plan markdown file
            prompt_file_path: Path to the YAML prompt template file
            figma_summary_path: Optional path to Figma summary file
            max_test_cases: Maximum number of test cases to process
            
        Returns:
            Dictionary containing the generated test suite
        """
        # Load test plan
        try:
            with open(test_plan_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        except Exception as e:
            raise ValueError(f"Error loading test plan file: {e}")

        # Load prompt template
        try:
            prompt_template = self.load_prompt_from_yaml(prompt_file_path, 'detailed_test_case_generation_prompt')
        except Exception as e:
            raise ValueError(f"Error loading prompt template: {e}")

        # Load Figma summary if provided
        figma_summary = ""
        if figma_summary_path and os.path.exists(figma_summary_path):
            try:
                with open(figma_summary_path, 'r', encoding='utf-8') as f:
                    figma_summary = f.read()
            except Exception as e:
                print(f"Warning: Could not load Figma summary: {e}")

        # Parse high-level test cases
        high_level_cases = self.parse_md_table(markdown_content)
        if not high_level_cases:
            raise ValueError("No test cases found in the markdown file")

        # Process test cases
        final_output = []
        test_count = 0
        
        for i, tc in enumerate(high_level_cases):
            if test_count >= max_test_cases:
                break
                
            print(f"\nProcessing case {i+1}/{len(high_level_cases)}: {tc.get('Test Case ID', 'N/A')}")
            
            # Prepare context for the AI prompt
            prompt_context = {
                "objective": "To ensure accurate, comprehensive, and consistent campaign performance tracking...",
                "test_case_id": tc.get('Test Case ID', 'N/A'),
                "scenario": tc.get('Test Scenario/Description', ''),
                "steps": tc.get('Test Steps', '').replace('<br>', '\n'),
                "expected_result": tc.get('Expected Result', '').replace('<br>', '\n'),
                "figma_summary": figma_summary
            }

            # Generate detailed steps
            detailed_steps = self.generate_detailed_steps(prompt_template, prompt_context)
            
            if not detailed_steps:
                print(f"Skipping bug report for {tc.get('Test Case ID', 'N/A')} due to generation error.")
                continue

            # Generate bug report template
            bug_report = self.generate_bug_report_template(tc, detailed_steps)
            
            # Assemble final object
            final_case_object = {
                "high_level_test_case": tc,
                "detailed_manual_test_case": detailed_steps,
                "sample_bug_report": bug_report
            }
            final_output.append(final_case_object)
            test_count += 1

        return {"test_suite": final_output}

    def save_test_suite(self, test_suite: Dict[str, Any], output_path: str = "test_suite.json") -> None:
        """Save the generated test suite to a JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(test_suite, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved test suite to '{output_path}'")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")


# --- CLI Interface ---

def main():
    """Command-line interface for the DetailedTestGenerator."""
    parser = argparse.ArgumentParser(description="Generate detailed test cases and bug reports from a Markdown test plan.")
    parser.add_argument("--test_plan", default="test_plan.md", help="Path to the input test_plan.md file.")
    parser.add_argument("--prompt_file", default="prompt_templates/test_designer.yaml", help="Path to the YAML file for detailed case generation.")
    parser.add_argument("--figma_summary", default="figma_summary.txt", help="Optional path to a Figma summary text file.")
    parser.add_argument("--max_test_cases", type=int, default=3, help="Maximum number of test cases to process.")
    parser.add_argument("--output", default="test_suite.json", help="Output JSON file path.")
    args = parser.parse_args()

    try:
        # Initialize generator
        generator = DetailedTestGenerator()
        
        # Generate test suite
        test_suite = generator.generate_detailed_test_suite(
            test_plan_path=args.test_plan,
            prompt_file_path=args.prompt_file,
            figma_summary_path=args.figma_summary,
            max_test_cases=args.max_test_cases
        )
        
        # Save results
        generator.save_test_suite(test_suite, args.output)
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
