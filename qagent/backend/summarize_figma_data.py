import json
import os
import argparse
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import yaml

class FigmaSummarizer:
    """Class for generating natural language summaries from Figma JSON data."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the FigmaSummarizer.
        
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

    def load_prompt_from_yaml(self, file_path: str) -> str:
        """Loads a specific prompt template from a YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['figma_summarization_prompt']

    def make_api_call(self, prompt: str) -> str:
        """Makes a single API call with retry logic."""
        generation_config = genai.types.GenerationConfig(response_mime_type="text/plain")
        
        max_retries = 5
        delay = 5
        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(contents=prompt, generation_config=generation_config)
                return response.text
            except google_exceptions.ResourceExhausted as e:
                print(f"Error: {e.message}")
                if attempt < max_retries - 1:
                    print(f"Quota exceeded. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise
        raise Exception("Failed to get a response from the API after multiple retries.")

    def load_figma_data(self, figma_path: str) -> Dict[str, Any]:
        """Load Figma data from JSON file."""
        try:
            with open(figma_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"The Figma file '{figma_path}' was not found.")
        except json.JSONDecodeError:
            raise ValueError(f"The Figma file '{figma_path}' is not a valid JSON file.")

    def generate_figma_summary(self, 
                             figma_path: str = "figma_data.json",
                             prompt_file: str = "prompt_templates/uiux_consultant.yaml") -> str:
        """
        Generate a natural language summary from Figma JSON data.
        
        Args:
            figma_path: Path to Figma JSON data file
            prompt_file: Path to YAML prompt template file
            
        Returns:
            Generated summary text
        """
        # Load Figma data
        figma_data = self.load_figma_data(figma_path)
        
        # Load prompt template
        try:
            prompt_template = self.load_prompt_from_yaml(prompt_file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template file '{prompt_file}' not found.")
        except KeyError:
            raise KeyError(f"'figma_summarization_prompt' key not found in '{prompt_file}'.")

        # Generate summary
        print("Generating Figma summary...")
        prompt = prompt_template.format(**figma_data)
        return self.make_api_call(prompt)

    def save_figma_summary(self, summary: str, output_path: str = "figma_summary.txt") -> None:
        """Save Figma summary to text file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(summary)
            print(f"Successfully saved Figma summary to '{output_path}'")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")


# --- CLI Interface ---

def main():
    """Command-line interface for the FigmaSummarizer."""
    parser = argparse.ArgumentParser(description="Generate a natural language summary from a Figma JSON file.")
    parser.add_argument("--figma", default="figma_data.json", help="Path to Figma JSON data file.")
    parser.add_argument("--prompt", default="prompt_templates/uiux_consultant.yaml", help="Path to YAML prompt template file.")
    parser.add_argument("--output", default="figma_summary.txt", help="Output text file path.")
    args = parser.parse_args()

    try:
        # Initialize summarizer
        summarizer = FigmaSummarizer()
        
        # Generate summary
        figma_summary = summarizer.generate_figma_summary(
            figma_path=args.figma,
            prompt_file=args.prompt
        )
        
        # Save results
        summarizer.save_figma_summary(figma_summary, args.output)
        
        print(f"\nSuccessfully generated and saved the Figma summary to '{args.output}'.")
        print("\n--- Summary ---")
        print(figma_summary)
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
