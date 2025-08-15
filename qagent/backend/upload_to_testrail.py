import json
import os
import argparse
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
from testrail import *

class TestRailAPI:
    """A simple client to interact with the TestRail API."""
    def __init__(self, base_url: str, user: str, password: str):
        self.client = APIClient(base_url=base_url)
        self.client.user = user
        self.client.password = password


    def add_section(self, project_id: int, data: Dict[str, any]) -> Dict:
        """Adds a new section to a specific project and suite.
        payload example:
        {
            'suite_id': int,
            'name': str,
            'parent_id': int (optional, default 0)
        }
        """
        return self.client.send_post(f'add_section/{project_id}', data)
    
    def add_case(self, section_id: int, data: Dict[str, Any]) -> Dict:
        """Adds a new test case to a specific section.
        {
            "title": "Verify successful display of BB Broadcast performance report.",
            "refs": "TC-BB-BR-001",
            "custom_preconds": "Preconditions: ...",
            "type_id": 7,
            "priority_id": 4,
            "labels": ["From Mindmeister"],
            "custom_steps_separated": [
                {
                "content": "1. Step 1.",
                "expected": "Expected result of Step 1."
                },
                {
                "content": "2. Step 2.",
                "expected": "Expected result of Step 2."
                }
            ]
        }
        """
        return self.client.send_post(f'add_case/{section_id}', data)

    def get_sections(self, project_id: str, suite_id: str) -> List[Dict]:
        """Gets all sections for a given project and suite."""
        return self.client.send_get(f'get_sections/{project_id}&suite_id={suite_id}')
    
    def delete_section(self, section_id: int) -> Dict:
        """Deletes a section by its ID."""
        return self.client.send_post(f'delete_section/{section_id}', {'soft': 0})

class TestRailUploader:
    """Handles loading a test plan from JSON and uploading it to TestRail, organizing cases by sections."""
    def __init__(self, json_path: str, project_id: int, suite_id: int):
        self.json_path = json_path
        self.project_id = project_id
        self.suite_id = suite_id
        self.sub_feature_tests = []
        self.preconditions = ""
        
        load_dotenv()
        testrail_url = os.getenv("TESTRAIL_URL")
        testrail_user = os.getenv("TESTRAIL_USER")
        testrail_key = os.getenv("TESTRAIL_PASSWORD_OR_KEY")

        if not all([testrail_url, testrail_user, testrail_key]):
            raise ValueError("TESTRAIL_URL, TESTRAIL_USER, and TESTRAIL_PASSWORD_OR_KEY must be set in .env file.")
        
        self.api = TestRailAPI(testrail_url, testrail_user, testrail_key)

    def _load_test_plan_from_json(self):
        """Loads the test plan data from the specified JSON file."""
        try:
            with open(self.json_path, 'r', encoding='utf-8') as f:
                test_plan_data = json.load(f)
            self.sub_feature_tests = test_plan_data.get("test_plan", {}).get("sub_feature_tests", [])
            for cond in test_plan_data.get("test_plan", {}).get("preconditions", ""):
                self.preconditions += "- " + cond + "\n"
            if not self.sub_feature_tests:
                print("No 'sub_feature_tests' found in the JSON file.")
                exit(0)
        except FileNotFoundError:
            print(f"Error: The file '{self.json_path}' was not found.")
            exit(1)
        except json.JSONDecodeError:
            print(f"Error: The file '{self.json_path}' is not a valid JSON file.")
            exit(1)

    @staticmethod
    def _create_payload_from_case(test_case_obj: Dict[str, Any], preconditions: str) -> Dict[str, Any]:
        """Formats a single test case object into the payload for the TestRail API."""
        priority_map = {"P0": 4, "P1": 3, "P2": 2, "P3": 1}

        payload = {
            "title": test_case_obj.get("test_scenario", "Untitled Test Case"),

            "refs": test_case_obj.get("test_case_id", ""),
            "custom_preconds": preconditions,
            "type_id": 7,
        }

        priority = test_case_obj.get("priority")
        if priority in priority_map:
            payload["priority_id"] = priority_map[priority]

        payload["labels"] = [test_case_obj.get("test_type", "")]

        if len(test_case_obj.get("test_steps", [])) == len(test_case_obj.get("expected_result", [])):
            payload["custom_steps_separated"] = []
            for i, step in enumerate(test_case_obj.get("test_steps", [])):
                new_step = {}
                new_step["content"] = f"{i+1}. {step}" 
                new_step["expected"] = test_case_obj.get("expected_result", [])[i]
                payload["custom_steps_separated"].append(new_step)
        else:
            # Format steps and expected results into Markdown lists for custom text fields
            payload["template_id"] = 1
            steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(test_case_obj.get("test_steps", [])))
            if steps_text:
                payload["custom_steps"] = steps_text

            expected_result_text = "\n".join(f"- {result}" for result in test_case_obj.get("expected_result", []))
            if expected_result_text:
                payload["custom_expected"] = expected_result_text

        return payload

    def upload_test_plan(self):
        """Orchestrates loading the plan and uploading sections and cases."""
        self._load_test_plan_from_json()
        
        try:
            print("Fetching existing sections from TestRail...")
            existing_sections = self.api.get_sections(self.project_id, self.suite_id)
            section_map = {section['name']: section['id'] for section in existing_sections['sections']}
            print(f"Found {len(section_map)} existing sections.")
        except Exception as e:
            print(f"Error fetching sections from TestRail: {e}")
            return

        total_cases_to_upload = sum(len(feature.get("test_cases", [])) for feature in self.sub_feature_tests)
        print(f"\nStarting to process {len(self.sub_feature_tests)} sub-features with a total of {total_cases_to_upload} test cases.")
        
        uploaded_count = 0
        for feature_group in self.sub_feature_tests:
            section_name = feature_group.get("sub_feature")
            if not section_name:
                print("Skipping a feature group with no 'sub_feature' name.")
                continue

            print(f"\n--- Processing Section: {section_name} ---")
            section_id = section_map.get(section_name)

            if not section_id:
                print(f"Section '{section_name}' not found. Creating it now...")
                try:
                    section_payload = {"suite_id": self.suite_id, "name": section_name}
                    new_section = self.api.add_section(self.project_id, section_payload)
                    section_id = new_section['id']
                    print(f"Successfully created section '{section_name}' with ID: {section_id}")
                except Exception as e:
                    print(f"FAILED to create section '{section_name}'. Error: {e}")
                    continue # Skip cases for this section if creation fails
            else:
                print(f"Found existing section '{section_name}' with ID: {section_id}")

            test_cases = feature_group.get("test_cases", [])
            for test_case in test_cases:
                uploaded_count += 1
                payload = self._create_payload_from_case(test_case, self.preconditions)
                try:
                    result = self.api.add_case(section_id, payload)
                    print(f"({uploaded_count}/{total_cases_to_upload}) Successfully uploaded '{result['title']}' as TestRail case C{result['id']}.")
                except Exception as e:
                    print(f"({uploaded_count}/{total_cases_to_upload}) FAILED to upload '{payload['title']}'. Error: {e}")
        print("\nUpload process complete.")

    def delete_all_sections(self):
        existing_sections = self.api.get_sections(self.project_id, self.suite_id)
        ids = [section['id'] for section in existing_sections['sections']]
        print(f"Deleting all sections in project {self.project_id} suite {self.suite_id}...")
        for id in ids: 
            self.api.delete_section(id)
        print(f"Deleted {len(ids)} sections.")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload a test plan from JSON to TestRail, creating sections for sub-features.")
    parser.add_argument("--json_path", help="Path to the input test plan JSON file.")
    parser.add_argument("--project_id", required=True, type=int, help="The ID of the project in TestRail.")
    parser.add_argument("--suite_id", required=True, type=int, help="The ID of the test suite in TestRail.")
    args = parser.parse_args()

    uploader = TestRailUploader(args.json_path, args.project_id, args.suite_id)
    # uploader.upload_test_plan()
    uploader.delete_all_sections()
