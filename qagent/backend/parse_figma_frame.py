import requests
import json
from typing import Dict, Any, List, Optional
import re

class FigmaFrameParser:
    """Class for parsing Figma frames and extracting interactive components."""
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the FigmaFrameParser.
        
        Args:
            access_token: Figma access token. If not provided, will try to load from environment.
        """
        if access_token is None:
            from dotenv import load_dotenv
            import os
            load_dotenv()
            access_token = os.getenv("FIGMA_ACCESS_TOKEN")
            if not access_token:
                raise ValueError("FIGMA_ACCESS_TOKEN not found in .env file or environment variables.")
        
        self.access_token = access_token

    def filter_component(self, figma_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Traverse frame node tree to extract interactive components."""
        results = []
        
        def traverse(node: Dict[str, Any], parent_id: Any = None):
            interactions = node.get("interactions", [])
            table = node.get("styleOverrideTable", [])
            # keep element if not decorative
            if (interactions or table):
                component = {
                    "parent_id": parent_id,
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "type": node.get("type"),
                    "position": {
                        "x": node.get("absoluteBoundingBox", {}).get("x"),
                        "y": node.get("absoluteBoundingBox", {}).get("y")
                    },
                    "size": {
                        "width": node.get("absoluteBoundingBox", {}).get("width"),
                        "height": node.get("absoluteBoundingBox", {}).get("height")
                    },
                    "interactions": node.get("interactions"),
                    "styleOverrideTable": node.get("styleOverrideTable")
                }
                results.append(component)
            for child in node.get("children", []):
                traverse(child, node.get("id"))
        
        # start from "document"
        if "document" in figma_data:
            traverse(figma_data["document"])
        
        return results

    def parse_figma_url(self, url: str) -> str:
        """
        Extract the file key from a Figma URL (supports /file/ or /design/ links).
        
        Args:
            url: Figma URL
            
        Returns:
            File key extracted from the URL
            
        Raises:
            ValueError: If URL format is invalid
        """
        pattern = r"https://www\.figma\.com/(file|design)/([a-zA-Z0-9]+)"
        match = re.search(pattern, url)
        if not match:
            raise ValueError("Invalid Figma URL format.")
        return match.group(2)

    def get_figma_file_data(self, file_key: str) -> Dict[str, Any]:
        """
        Retrieve a specific frame from Figma API.
        
        Args:
            file_key: Figma file key
            
        Returns:
            JSON response from Figma API
            
        Raises:
            requests.RequestException: If API request fails
        """
        headers = {
            'X-Figma-Token': self.access_token
        }
        url = f"https://api.figma.com/v1/files/{file_key}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def parse_figma_frame_from_url(self, figma_url: str) -> Dict[str, Any]:
        """
        Parse Figma frame from URL and extract interactive components.
        
        Args:
            figma_url: Figma design/file URL
            
        Returns:
            Dictionary containing filtered Figma data
        """
        file_key = self.parse_figma_url(figma_url)
        figma_data = self.get_figma_file_data(file_key)
        filtered_components = self.filter_component(figma_data)
        
        return {
            "figma_data": filtered_components,
        }

    def save_figma_data(self, figma_data: Dict[str, Any], output_path: str = "figma_data.json") -> None:
        """Save Figma data to JSON file."""
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(figma_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved Figma data to '{output_path}'")
        except IOError as e:
            raise IOError(f"Error writing to file '{output_path}': {e}")


# --- CLI Interface ---

def main():
    """Command-line interface for the FigmaFrameParser."""
    import argparse
    from dotenv import load_dotenv
    import os
    
    parser = argparse.ArgumentParser(description="Get Figma frame from Figma URL")
    parser.add_argument("fig_url", help="Figma design/file URL")
    parser.add_argument("--output", default="figma_data.json", help="Output JSON file path.")
    args = parser.parse_args()

    try:
        # Initialize parser
        parser_instance = FigmaFrameParser()
        
        # Parse Figma frame
        result = parser_instance.parse_figma_frame_from_url(args.fig_url)
        
        # Save results
        parser_instance.save_figma_data(result, args.output)
        
    except Exception as e:
        print(f"Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
