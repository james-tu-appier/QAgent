import json
import argparse
import os
from typing import Dict, Any

class MarkdownFormatter:
    """Class for converting JSON test plans and test suites to Markdown format."""
    
    def convert_test_plan_json_to_md(self, data: Dict[str, Any]) -> str:
        """
        Converts a test plan dictionary (from JSON) into a formatted Markdown string.

        Args:
            data: A dictionary containing the test plan data.

        Returns:
            A string containing the test plan in Markdown format.
        """
        if "test_plan" not in data:
            return "# Error: 'test_plan' key not found in JSON data."

        plan = data["test_plan"]
        md_lines = []

        # --- Header ---
        md_lines.append(f"# Test Plan Guidelines: {plan.get('feature', 'N/A')}")
        md_lines.append(f"**Test Plan ID:** `{plan.get('test_plan_id', 'N/A')}`\n")
        md_lines.append(f"**Objective:** {plan.get('objective', 'N/A')}\n")

        # --- Preconditions ---
        md_lines.append("## Preconditions")
        preconditions = plan.get('preconditions', [])
        if preconditions:
            for item in preconditions:
                md_lines.append(f"- {item}")
        else:
            md_lines.append("- None specified.")
        md_lines.append("\n---\n")

        # --- Test Cases by Sub-Feature ---
        sub_feature_tests = plan.get('sub_feature_tests', [])
        for feature_group in sub_feature_tests:
            sub_feature_name = feature_group.get('sub_feature', 'Unnamed Sub-Feature')
            md_lines.append(f"## Test Cases for: {sub_feature_name}\n")

            # --- Table Header ---
            md_lines.append("| Test Case ID | Test Scenario/Description | Test Steps | Expected Result | Rationale / Business Impact | Test Type | Priority |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

            # --- Table Rows ---
            test_cases = feature_group.get('test_cases', [])
            for case in test_cases:
                # Format multi-line steps and results for Markdown table cells
                steps = "<br>".join(f"{i+1}. {step}" for i, step in enumerate(case.get('test_steps', [])))
                results = "<br>".join(f"- {res}" for res in case.get('expected_result', []))

                row = [
                    f"`{case.get('test_case_id', '')}`",
                    case.get('test_scenario', ''),
                    steps,
                    results,
                    case.get('Rationale / Business Impact', ''), # Handle alias
                    case.get('test_type', ''),
                    case.get('priority', '')
                ]
                md_lines.append("| " + " | ".join(row) + " |")
            
            md_lines.append("\n")

        return "\n".join(md_lines)

    def convert_test_suite_json_to_md(self, test_suite_data: Dict[str, Any]) -> str:
        """
        Converts a detailed test suite JSON object into a single, comprehensive Markdown document.

        Args:
            test_suite_data: A dictionary containing the test suite data.

        Returns:
            A string containing the entire test suite in Markdown format.
        """
        if "test_suite" not in test_suite_data:
            return "# Error: 'test_suite' key not found in JSON data."

        md_lines = ["# Detailed Manual Test Suite"]
        
        for test_case_obj in test_suite_data["test_suite"]:
            high_level_case = test_case_obj.get("high_level_test_case", {})
            detailed_steps = test_case_obj.get("detailed_manual_test_case", [])
            bug_report = test_case_obj.get("sample_bug_report", "")

            # --- Test Case Header ---
            tc_id = high_level_case.get("Test Case ID", "N/A")
            scenario = high_level_case.get("Test Scenario/Description", "N/A")
            md_lines.append(f"\n---\n\n## Test Case: `{tc_id}` - {scenario}")
            
            # --- High-Level Summary Table ---
            md_lines.append("\n### Summary\n")
            md_lines.append("| Priority | Test Type | Rationale / Business Impact |")
            md_lines.append("| :--- | :--- | :--- |")
            md_lines.append(
                f"| {high_level_case.get('Priority', 'N/A')} "
                f"| {high_level_case.get('Test Type', 'N/A')} "
                f"| {high_level_case.get('Rationale / Business Impact', 'N/A')} |"
            )
            
            # --- Detailed Manual Steps Table ---
            md_lines.append("\n### Detailed Steps\n")
            md_lines.append("| Step | Action | Expected Result |")
            md_lines.append("| :--- | :--- | :--- |")
            for step in detailed_steps:
                md_lines.append(
                    f"| {step.get('step_number', '')} "
                    f"| {step.get('action', '')} "
                    f"| {step.get('expected_result', '')} |"
                )
                
            # --- Sample Bug Report ---
            md_lines.append("\n### Sample Bug Report Template\n")
            # Format bug report as a blockquote for visual separation
            indented_bug_report = "\n".join([f"> {line}" for line in bug_report.split('\n')])
            md_lines.append(indented_bug_report)

        return "\n".join(md_lines)

    def load_json_file(self, json_path: str) -> Dict[str, Any]:
        """Load JSON data from file."""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{json_path}' was not found.")
        except json.JSONDecodeError:
            raise ValueError(f"The file '{json_path}' is not a valid JSON file.")

    def save_markdown_file(self, markdown_content: str, output_path: str) -> None:
        """Save markdown content to file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Successfully converted and saved to '{output_path}'.")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")

    def convert_test_plan(self, json_path: str, output_path: str = "test_plan.md") -> None:
        """Convert test plan JSON to Markdown and save to file."""
        json_data = self.load_json_file(json_path)
        markdown_content = self.convert_test_plan_json_to_md(json_data)
        self.save_markdown_file(markdown_content, output_path)

    def convert_test_suite(self, json_path: str, output_path: str = "test_suite.md") -> None:
        """Convert test suite JSON to Markdown and save to file."""
        json_data = self.load_json_file(json_path)
        markdown_content = self.convert_test_suite_json_to_md(json_data)
        self.save_markdown_file(markdown_content, output_path)


# --- CLI Interface ---

def main():
    """Command-line interface for the MarkdownFormatter."""
    parser = argparse.ArgumentParser(description="Convert a test plan/test suite from JSON format to Markdown.")
    parser.add_argument("--type", required=True, help="test_plan or test_suite")
    parser.add_argument("--json_path", required=True, help="Path to the input JSON file.")
    parser.add_argument("--output", help="Output Markdown file path (optional).")
    args = parser.parse_args()
    
    if args.type not in ["test_plan", "test_suite"]:
        print("Error: --type must be either 'test_plan' or 'test_suite'.")
        exit(1)

    try:
        # Initialize formatter
        formatter = MarkdownFormatter()
        
        # Set default output path if not provided
        if not args.output:
            args.output = f"{args.type}.md"
        
        # Convert based on type
        if args.type == "test_plan":
            formatter.convert_test_plan(args.json_path, args.output)
        elif args.type == "test_suite":
            formatter.convert_test_suite(args.json_path, args.output)
            
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()




