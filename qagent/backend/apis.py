"""
Example demonstrating how to use the refactored classes in a backend API context.

This file shows how to integrate all the test planning classes into a Flask/FastAPI backend
or any other web framework.
"""

import os
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Import all the refactored classes
from prd_to_specs import PRDExtractor
from parse_figma_frame import FigmaFrameParser
from summarize_figma_data import FigmaSummarizer
from generate_test_plan import TestPlanGenerator
from generate_detailed_tests import DetailedTestGenerator
from json_to_md_formatter import MarkdownFormatter


class TestPlanningAPI:
    """
    Main API class that orchestrates the entire test planning workflow.
    
    This class demonstrates how to use all the refactored classes together
    to create a complete test planning pipeline.
    """
    
    def __init__(self, gemini_api_key: Optional[str] = None, figma_token: Optional[str] = None):
        """
        Initialize the TestPlanningAPI with all required services.
        
        Args:
            gemini_api_key: Gemini API key for AI operations
            figma_token: Figma access token for design parsing
        """
        # Load environment variables if not provided
        if gemini_api_key is None or figma_token is None:
            load_dotenv()
            if gemini_api_key is None:
                gemini_api_key = os.getenv("GEMINI_API_KEY")
            if figma_token is None:
                figma_token = os.getenv("FIGMA_ACCESS_TOKEN")
        
        # Initialize all service classes
        self.prd_extractor = PRDExtractor(api_key=gemini_api_key)
        self.figma_parser = FigmaFrameParser(access_token=figma_token)
        self.figma_summarizer = FigmaSummarizer(api_key=gemini_api_key)
        self.test_plan_generator = TestPlanGenerator(api_key=gemini_api_key)
        self.detailed_test_generator = DetailedTestGenerator(api_key=gemini_api_key)
        self.markdown_formatter = MarkdownFormatter()
    
    def extract_prd_context(self, prd_file_path: str) -> Dict[str, Any]:
        """
        Extract structured context from a PRD file.
        
        Args:
            prd_file_path: Path to PRD file (PDF or text)
            
        Returns:
            Extracted PRD context
        """
        return self.prd_extractor.extract_prd_from_file(prd_file_path)
    
    def parse_figma_design(self, figma_url: str) -> Dict[str, Any]:
        """
        Parse Figma design and extract interactive components.
        
        Args:
            figma_url: Figma design URL
            
        Returns:
            Parsed Figma data
        """
        return self.figma_parser.parse_figma_frame_from_url(figma_url)
    
    def summarize_figma_data(self, figma_data: Dict[str, Any]) -> str:
        """
        Generate natural language summary from Figma data.
        
        Args:
            figma_data: Parsed Figma data
            
        Returns:
            Generated summary
        """
        # Save figma data temporarily for the summarizer
        temp_path = "temp_figma_data.json"
        self.figma_parser.save_figma_data(figma_data, temp_path)
        
        try:
            summary = self.figma_summarizer.generate_figma_summary(temp_path)
            return summary
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def generate_test_plan(self, prd_context: Dict[str, Any], figma_summary: str = "") -> Dict[str, Any]:
        """
        Generate test plan from PRD context and optional Figma summary.
        
        Args:
            prd_context: Extracted PRD context
            figma_summary: Generated Figma summary (optional)
            
        Returns:
            Generated test plan
        """
        # Save PRD context temporarily
        temp_prd_path = "temp_prd_context.json"
        self.prd_extractor.save_prd_context(prd_context, temp_prd_path)
        
        # Save Figma summary temporarily (or create empty file if no summary)
        temp_figma_path = "temp_figma_summary.txt"
        if figma_summary:
            self.figma_summarizer.save_figma_summary(figma_summary, temp_figma_path)
        else:
            with open(temp_figma_path, "w") as f:
                f.write("No Figma data provided")
        
        try:
            test_plan = self.test_plan_generator.generate_test_plan_from_files(
                context_path=temp_prd_path,
                figma_path=temp_figma_path
            )
            return test_plan
        finally:
            # Clean up temporary files
            for temp_file in [temp_prd_path, temp_figma_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def generate_detailed_tests(self, test_plan: Dict[str, Any], figma_summary: str = "") -> Dict[str, Any]:
        """
        Generate detailed test cases from test plan.
        
        Args:
            test_plan: Generated test plan
            figma_summary: Figma summary for context (optional)
            
        Returns:
            Detailed test suite
        """
        # Save test plan temporarily as markdown
        temp_test_plan_path = "temp_test_plan.md"
        self.markdown_formatter.convert_test_plan(test_plan, temp_test_plan_path)
        
        # Save Figma summary temporarily (or create empty file if no summary)
        temp_figma_path = "temp_figma_summary.txt"
        if figma_summary:
            self.figma_summarizer.save_figma_summary(figma_summary, temp_figma_path)
        else:
            with open(temp_figma_path, "w") as f:
                f.write("No Figma data provided")
        
        try:
            detailed_tests = self.detailed_test_generator.generate_detailed_test_suite(
                test_plan_path=temp_test_plan_path,
                figma_summary_path=temp_figma_path
            )
            return detailed_tests
        finally:
            # Clean up temporary files
            for temp_file in [temp_test_plan_path, temp_figma_path]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
    
    def convert_to_markdown(self, data: Dict[str, Any], data_type: str) -> str:
        """
        Convert JSON data to Markdown format.
        
        Args:
            data: JSON data to convert
            data_type: Type of data ('test_plan' or 'test_suite')
            
        Returns:
            Markdown formatted string
        """
        if data_type == "test_plan":
            return self.markdown_formatter.convert_test_plan_json_to_md(data)
        elif data_type == "test_suite":
            return self.markdown_formatter.convert_test_suite_json_to_md(data)
        else:
            raise ValueError("data_type must be 'test_plan' or 'test_suite'")
    
    def run_complete_workflow(self, 
                            prd_file_path: str, 
                            figma_url: str = "",
                            output_dir: str = "output") -> Dict[str, Any]:
        """
        Run the complete test planning workflow.
        
        Args:
            prd_file_path: Path to PRD file
            figma_url: Figma design URL (optional)
            output_dir: Directory to save output files
            
        Returns:
            Dictionary containing all generated outputs
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        print("Step 1: Extracting PRD context...")
        prd_context = self.extract_prd_context(prd_file_path)
        self.prd_extractor.save_prd_context(prd_context, f"{output_dir}/prd_context.json")
        
        # Step 2: Parse Figma design (optional)
        figma_data = None
        figma_summary = ""
        if figma_url and figma_url.strip():
            print("Step 2: Parsing Figma design...")
            figma_data = self.parse_figma_design(figma_url)
            self.figma_parser.save_figma_data(figma_data, f"{output_dir}/figma_data.json")
            
            print("Step 3: Summarizing Figma data...")
            figma_summary = self.summarize_figma_data(figma_data)
            self.figma_summarizer.save_figma_summary(figma_summary, f"{output_dir}/figma_summary.txt")
        else:
            print("Step 2: Skipping Figma parsing (no URL provided)")
            # Create empty figma files for consistency
            with open(f"{output_dir}/figma_data.json", "w") as f:
                json.dump({}, f)
            with open(f"{output_dir}/figma_summary.txt", "w") as f:
                f.write("No Figma data provided")
        
        print("Step 4: Generating test plan...")
        test_plan = self.generate_test_plan(prd_context, figma_summary)
        self.test_plan_generator.save_test_plan(test_plan, f"{output_dir}/test_plan.json")
        
        print("Step 5: Converting test plan to Markdown...")
        test_plan_md = self.convert_to_markdown(test_plan, "test_plan")
        with open(f"{output_dir}/test_plan.md", "w") as f:
            f.write(test_plan_md)
        
        print("Step 6: Generating detailed test cases...")
        detailed_tests = self.generate_detailed_tests(test_plan, figma_summary)
        self.detailed_test_generator.save_test_suite(detailed_tests, f"{output_dir}/test_suite.json")
        
        print("Step 7: Converting detailed tests to Markdown...")
        test_suite_md = self.convert_to_markdown(detailed_tests, "test_suite")
        with open(f"{output_dir}/test_suite.md", "w") as f:
            f.write(test_suite_md)
        
        return {
            "prd_context": prd_context,
            "figma_data": figma_data,
            "figma_summary": figma_summary,
            "test_plan": test_plan,
            "detailed_tests": detailed_tests,
            "output_files": {
                "prd_context": f"{output_dir}/prd_context.json",
                "figma_data": f"{output_dir}/figma_data.json",
                "figma_summary": f"{output_dir}/figma_summary.txt",
                "test_plan_json": f"{output_dir}/test_plan.json",
                "test_plan_md": f"{output_dir}/test_plan.md",
                "test_suite_json": f"{output_dir}/test_suite.json",
                "test_suite_md": f"{output_dir}/test_suite.md"
            }
        }


# Example usage for Flask API
def create_flask_app():
    """Example Flask app showing how to integrate the classes."""
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    api = TestPlanningAPI()
    
    @app.route('/extract-prd', methods=['POST'])
    def extract_prd():
        """Extract PRD context from uploaded file."""
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        file.save(temp_path)
        
        try:
            prd_context = api.extract_prd_context(temp_path)
            return jsonify(prd_context)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @app.route('/parse-figma', methods=['POST'])
    def parse_figma():
        """Parse Figma design from URL."""
        data = request.get_json()
        if not data or 'figma_url' not in data:
            return jsonify({"error": "Figma URL required"}), 400
        
        try:
            figma_data = api.parse_figma_design(data['figma_url'])
            return jsonify(figma_data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/generate-test-plan', methods=['POST'])
    def generate_test_plan():
        """Generate test plan from PRD context and optional Figma summary."""
        data = request.get_json()
        if not data or 'prd_context' not in data:
            return jsonify({"error": "PRD context required"}), 400
        
        try:
            figma_summary = data.get('figma_summary', '')
            test_plan = api.generate_test_plan(data['prd_context'], figma_summary)
            return jsonify(test_plan)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/generate-detailed-tests', methods=['POST'])
    def generate_detailed_tests():
        """Generate detailed test cases from test plan."""
        data = request.get_json()
        if not data or 'test_plan' not in data:
            return jsonify({"error": "Test plan required"}), 400
        
        try:
            figma_summary = data.get('figma_summary', '')
            detailed_tests = api.generate_detailed_tests(data['test_plan'], figma_summary)
            return jsonify(detailed_tests)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/convert-to-markdown', methods=['POST'])
    def convert_to_markdown():
        """Convert JSON data to Markdown format."""
        data = request.get_json()
        if not data or 'data' not in data or 'type' not in data:
            return jsonify({"error": "Data and type required"}), 400
        
        try:
            markdown = api.convert_to_markdown(data['data'], data['type'])
            return jsonify({"markdown": markdown})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/complete-workflow', methods=['POST'])
    def complete_workflow():
        """Run the complete test planning workflow."""
        data = request.get_json()
        if not data or 'prd_file_path' not in data:
            return jsonify({"error": "PRD file path required"}), 400
        
        try:
            figma_url = data.get('figma_url', '')
            result = api.run_complete_workflow(
                data['prd_file_path'],
                figma_url,
                data.get('output_dir', 'output')
            )
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app


# Example usage for FastAPI
def create_fastapi_app():
    """Example FastAPI app showing how to integrate the classes."""
    from fastapi import FastAPI, File, UploadFile, HTTPException
    from pydantic import BaseModel
    
    app = FastAPI()
    api = TestPlanningAPI()
    
    class FigmaRequest(BaseModel):
        figma_url: str
    
    class TestPlanRequest(BaseModel):
        prd_context: Dict[str, Any]
        figma_summary: str = ""
    
    class DetailedTestsRequest(BaseModel):
        test_plan: Dict[str, Any]
        figma_summary: str = ""
    
    class MarkdownRequest(BaseModel):
        data: Dict[str, Any]
        type: str
    
    class WorkflowRequest(BaseModel):
        prd_file_path: str
        figma_url: str = ""
        output_dir: str = "output"
    
    @app.post("/extract-prd")
    async def extract_prd(file: UploadFile = File(...)):
        """Extract PRD context from uploaded file."""
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Save uploaded file temporarily
        temp_path = f"temp_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            prd_context = api.extract_prd_context(temp_path)
            return prd_context
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    @app.post("/parse-figma")
    async def parse_figma(request: FigmaRequest):
        """Parse Figma design from URL."""
        try:
            figma_data = api.parse_figma_design(request.figma_url)
            return figma_data
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/generate-test-plan")
    async def generate_test_plan(request: TestPlanRequest):
        """Generate test plan from PRD context and Figma summary."""
        try:
            test_plan = api.generate_test_plan(request.prd_context, request.figma_summary)
            return test_plan
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/generate-detailed-tests")
    async def generate_detailed_tests(request: DetailedTestsRequest):
        """Generate detailed test cases from test plan."""
        try:
            detailed_tests = api.generate_detailed_tests(request.test_plan, request.figma_summary)
            return detailed_tests
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/convert-to-markdown")
    async def convert_to_markdown(request: MarkdownRequest):
        """Convert JSON data to Markdown format."""
        try:
            markdown = api.convert_to_markdown(request.data, request.type)
            return {"markdown": markdown}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/complete-workflow")
    async def complete_workflow(request: WorkflowRequest):
        """Run the complete test planning workflow."""
        try:
            result = api.run_complete_workflow(
                request.prd_file_path,
                request.figma_url,
                request.output_dir
            )
            return result
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


if __name__ == "__main__":
    # Example usage of the TestPlanningAPI class
    print("Example: Using TestPlanningAPI class directly")
    
    # Initialize the API
    api = TestPlanningAPI()
    
    # Example: Run complete workflow (uncomment and modify paths as needed)
    # result = api.run_complete_workflow(
    #     prd_file_path="path/to/your/prd.pdf",
    #     figma_url="https://www.figma.com/file/your-file-key",
    #     output_dir="my_test_plan_output"
    # )
    # print("Workflow completed successfully!")
    # print(f"Output files saved to: {result['output_files']}")
    
    print("API classes are ready for integration into your backend!") 