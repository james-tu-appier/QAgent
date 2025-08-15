import json
import os
import argparse
import time
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import PyPDF2
import yaml

# --- Pydantic Models for Structured PRD Output ---
# This schema defines the structure of the data we want to extract from the PRD.
# It's designed to capture information most relevant for test planning.

class TechSpecs(BaseModel):
    """Detailed technical specifications extracted from the PRD."""
    system_interactions: List[str] = Field(..., description="Descriptions of how different systems, services, or components interact with each other.")
    data_models_or_schemas: List[str] = Field(..., description="Details on new or modified data structures, database tables, or API schemas.")
    api_endpoints: List[str] = Field(..., description="List of relevant API endpoints mentioned, including HTTP methods if available.")
    authentication_and_authorization: List[str] = Field(..., description="Notes on user permissions, roles, or authentication requirements.")

class OtherDataForTesting(BaseModel):
    """Captures other contextual information crucial for comprehensive test design."""
    acceptance_criteria: List[str] = Field(..., description="Specific, testable criteria that must be met for a user story or feature to be considered complete.")
    dependencies_and_integrations: List[str] = Field(..., description="Other features, systems, or external services that this feature depends on or integrates with.")
    known_limitations_or_risks: List[str] = Field(..., description="Any known limitations, out-of-scope items, or potential risks mentioned in the document.")
    success_metrics: List[str] = Field(..., description="Metrics or KPIs that will be used to measure the success of the feature.")

class ExtractedPRDContext(BaseModel):
    """The root object for all information extracted from the PRD."""
    project_name: str = Field(..., description="The official name of the project or feature.")
    target_feature_summary: str = Field(..., description="A concise summary of the feature's purpose and the core problem it solves.")
    core_user_stories: List[str] = Field(..., description="A list of all user stories mentioned in the document.")
    technical_specifications: TechSpecs
    other_contextual_data: OtherDataForTesting

class PRDResponse(BaseModel):
    """The final response schema expected from the Gemini API."""
    prd_context: ExtractedPRDContext

class PRDExtractor:
    """Class for extracting structured information from PRD documents."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the PRDExtractor.
        
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

    def extract_prd_info(self, prompt_template: str, prd_text_content: str) -> Dict:
        """
        Parses a PRD's text content to extract key information for test planning using the Gemini API.

        Args:
            prompt_template: The prompt template string with a {prd_content} placeholder.
            prd_text_content: The full text content of the Product Requirements Document.

        Returns:
            A dictionary containing the structured information extracted from the PRD.
        """
        # Format the prompt with the actual PRD content
        prompt = prompt_template.format(prd_content=prd_text_content)

        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json",
            response_schema=PRDResponse,
        )

        max_retries = 5
        delay = 5  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                print("Analyzing PRD and extracting information...")
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

    def get_text_from_pdf(self, pdf_path: str) -> str:
        """Extracts text from all pages of a PDF file."""
        text = ""
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def load_prompt_from_yaml(self, file_path: str) -> str:
        """Loads the prompt template from a YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['prd_parsing_prompt']

    def load_prd_content(self, prd_path: str) -> str:
        """Load PRD content from file (PDF or text)."""
        try:
            file_extension = os.path.splitext(prd_path)[1].lower()
            if file_extension == ".pdf":
                print(f"PDF file detected. Extracting text from '{prd_path}'...")
                return self.get_text_from_pdf(prd_path)
            else:
                print(f"Text file detected. Reading from '{prd_path}'...")
                with open(prd_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{prd_path}' was not found.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the file: {e}")

    def extract_prd_from_file(self, 
                            prd_path: str, 
                            prompt_file_path: str = "prompt_templates/prd_reader.yaml") -> Dict:
        """
        Extract structured information from a PRD file.
        
        Args:
            prd_path: Path to the PRD file (PDF or text)
            prompt_file_path: Path to the YAML prompt template file
            
        Returns:
            Dictionary containing the extracted PRD context
        """
        # Load PRD content
        prd_content = self.load_prd_content(prd_path)
        
        if not prd_content.strip():
            raise ValueError("No text could be extracted from the document. The file might be empty or unreadable.")

        # Load prompt template
        try:
            prompt_template = self.load_prompt_from_yaml(prompt_file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template file '{prompt_file_path}' not found.")
        except KeyError:
            raise KeyError(f"'prd_parsing_prompt' key not found in '{prompt_file_path}'.")

        # Extract information
        return self.extract_prd_info(prompt_template, prd_content)

    def save_prd_context(self, extracted_data: Dict, output_path: str = "prd_context.json") -> None:
        """Save the extracted PRD context to a JSON file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved PRD context to '{output_path}'")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")


# --- CLI Interface ---

def main():
    """Command-line interface for the PRDExtractor."""
    parser = argparse.ArgumentParser(description="Extract structured information from a PRD file (txt or pdf) for test planning.")
    parser.add_argument("prd_path", help="Path to the PRD file.")
    parser.add_argument("--prompt", default="prompt_templates/prd_reader.yaml", help="Path to YAML prompt template file.")
    parser.add_argument("--output", default="prd_context.json", help="Output JSON file path.")
    args = parser.parse_args()

    try:
        # Initialize extractor
        extractor = PRDExtractor()
        
        # Extract PRD information
        extracted_data = extractor.extract_prd_from_file(
            prd_path=args.prd_path,
            prompt_file_path=args.prompt
        )
        
        # Save results
        extractor.save_prd_context(extracted_data, args.output)
        
        print(f"\nSuccessfully extracted PRD context and saved it to '{args.output}'.")
        if extracted_data:
            print("\n--- Extracted Project Name ---")
            print(extracted_data.get("prd_context", {}).get("project_name"))
            print("\n--- Extracted Feature Summary ---")
            print(extracted_data.get("prd_context", {}).get("target_feature_summary"))
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
