import json
import os
import argparse
import time
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import yaml

# --- Pydantic Models Based on the Prioritized Test Plan Template ---
class TestCase(BaseModel):
    """Represents a single row in the test case table."""
    test_case_id: str = Field(..., description="A unique identifier for the test case, e.g., 'TC-BB-001'.")
    test_scenario: str = Field(..., description="A clear, concise description of the test scenario.")
    test_steps: List[str] = Field(..., description="A list of numbered steps to execute the test.")
    expected_result: List[str] = Field(..., description="A list of expected outcomes after executing the test steps.")
    rationale: str = Field(..., alias="Rationale / Business Impact", description="Justification for the test, linking it to a user story or business risk.")
    test_type: str = Field(..., description="The category of testing, e.g., 'Functional', 'Negative', 'UI'.")
    priority: str = Field(..., description="The priority of the test case, e.g., 'P0', 'P1', 'P2'.")

class TestCasesForSubFeature(BaseModel):
    """Groups test cases under a specific sub-feature."""
    sub_feature: str = Field(..., description="The name of the sub-feature being tested, e.g., 'BB Broadcast Performance Report'.")
    test_cases: List[TestCase]

class TestPlan(BaseModel):
    """The root object for the entire test plan for a major feature."""
    test_plan_id: str = Field(..., description="A unique ID for the overall test plan, e.g., 'TP-CONV-TRACK-001'.")
    feature: str = Field(..., description="The high-level feature covered by this test plan.")
    objective: str = Field(..., description="The primary goal of this test plan.")
    preconditions: List[str] = Field(..., description="A list of conditions that must be met before testing begins.")
    sub_feature_tests: List[TestCasesForSubFeature]

class TestPlanResponse(BaseModel):
    """The final response schema expected from the Gemini API."""
    test_plan: TestPlan

class TestPlanGenerator:
    """Class for generating test plans from PRD context and Figma data."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the TestPlanGenerator.
        
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

    def generate_test_plan(self, prompt_template: str, context: Dict) -> Dict:
        """
        Generates a prioritized E2E test plan using the Gemini API based on a detailed prompt template.

        Args:
            prompt_template: The prompt template string with placeholders.
            context: A dictionary containing the data to format the prompt.

        Returns:
            A dictionary containing the generated test plan.
        """
        # Format the prompt with the context data
        prompt = prompt_template.format(**context)

        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            response_schema=TestPlanResponse,
        )

        max_retries = 5
        delay = 5  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                print("Generating test plan... This may take a moment.")
                response = self.model.generate_content(
                    contents=prompt,
                    generation_config=generation_config
                )
                return json.loads(response.text)
            except google_exceptions.ResourceExhausted as e:
                print(f"Error: {e.message}")
                if attempt < max_retries - 1:
                    print(f"Quota exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    print("Maximum retries reached. Aborting.")
                    raise
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                raise

        raise Exception("Failed to get a response from the API after multiple retries.")

    def load_prompt_from_yaml(self, file_path: str) -> str:
        """Loads the prompt template from a YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['test_plan_generation_prompt']

    def load_prd_context(self, context_path: str) -> Dict:
        """Load PRD context from JSON file."""
        try:
            with open(context_path, "r", encoding="utf-8") as f:
                prd_context_data = json.load(f).get("prd_context", {})
                return prd_context_data
        except FileNotFoundError:
            raise FileNotFoundError(f"The context file '{context_path}' was not found.")
        except json.JSONDecodeError:
            raise ValueError(f"The context file '{context_path}' is not a valid JSON file.")

    def load_figma_summary(self, figma_path: str) -> str:
        """Load Figma summary from text file."""
        try:
            with open(figma_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"The Figma file '{figma_path}' was not found.")

    def generate_test_plan_from_files(self, 
                                    context_path: str = "prd_context.json",
                                    figma_path: str = "figma_summary.txt",
                                    prompt_path: str = "prompt_templates/test_planner.yaml",
                                    additional_notes: str = "") -> Dict:
        """
        Generate test plan from PRD context and Figma files.
        
        Args:
            context_path: Path to PRD context JSON file
            figma_path: Path to Figma summary text file
            prompt_path: Path to YAML prompt template file
            additional_notes: Additional notes to include in the context
            
        Returns:
            Dictionary containing the generated test plan
        """
        # Load PRD context
        prd_context_data = self.load_prd_context(context_path)
        prd_context_data["additional_notes"] = additional_notes

        # Load Figma data
        figma_summary = self.load_figma_summary(figma_path)

        # Load prompt template
        try:
            prompt_template = self.load_prompt_from_yaml(prompt_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template file '{prompt_path}' not found.")
        except KeyError:
            raise KeyError(f"'test_plan_generation_prompt' key not found in '{prompt_path}'.")

        # Prepare the context dictionary for prompt formatting
        prompt_context = {
            "project_name": prd_context_data.get("project_name", "N/A"),
            "target_feature": prd_context_data.get("target_feature_summary", "N/A"),
            "core_user_stories": prd_context_data.get("core_user_stories", []),
            "tech_specs": json.dumps(prd_context_data.get("technical_specifications", {}), indent=2),
            "figma_summary": figma_summary,
            "additional_notes": additional_notes
        }

        # Generate the test plan
        return self.generate_test_plan(
            prompt_template=prompt_template,
            context=prompt_context
        )

    def save_test_plan(self, test_plan: Dict, output_path: str = "test_plan.json") -> None:
        """Save the generated test plan to a JSON file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(test_plan, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved test plan to '{output_path}'")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")


# --- CLI Interface ---

def main():
    """Command-line interface for the TestPlanGenerator."""
    parser = argparse.ArgumentParser(description="Generate a test plan from PRD context and Figma JSON files.")
    parser.add_argument("--context", default="prd_context.json", help="Path to PRD context JSON file.")
    parser.add_argument("--figma", default="figma_summary.txt", help="Path to Figma summary text file.")
    parser.add_argument("--prompt", default="prompt_templates/test_planner.yaml", help="Path to YAML prompt template file.")
    parser.add_argument("--notes", default="", help="Additional notes to include in the context.")
    parser.add_argument("--output", default="test_plan.json", help="Output JSON file path.")
    args = parser.parse_args()

    try:
        # Initialize generator
        generator = TestPlanGenerator()
        
        # Generate test plan
        result = generator.generate_test_plan_from_files(
            context_path=args.context,
            figma_path=args.figma,
            prompt_path=args.prompt,
            additional_notes=args.notes
        )
        
        # Save results
        generator.save_test_plan(result, args.output)
        
        print(f"\nSuccessfully generated and saved the test plan to '{args.output}'.")
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
