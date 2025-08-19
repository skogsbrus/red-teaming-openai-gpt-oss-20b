#!/usr/bin/env python3
"""
JSON Schema Validator for Red Team Findings

This script validates JSON files against the red team findings schema.
Usage: python validate_json.py <json_file> [schema_file]

If schema_file is not provided, it defaults to competition/samples/findings.schema
"""

import json
import sys
import argparse
from pathlib import Path

try:
    import jsonschema
    from jsonschema import validate, ValidationError, Draft202012Validator
except ImportError:
    print("Error: jsonschema library not found. Install it with:")
    print("pip install jsonschema")
    sys.exit(1)


def load_json_file(file_path):
    """Load and parse a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{file_path}': {e}")
        sys.exit(1)


def validate_json_against_schema(json_data, schema_data, json_file_path):
    """Validate JSON data against schema and print results."""
    try:
        # Create validator with Draft 2020-12 support
        validator = Draft202012Validator(schema_data)
        
        # Validate the JSON
        validator.validate(json_data)
        
        print(f"✅ '{json_file_path}' is VALID according to the schema!")
        return True
        
    except ValidationError as e:
        print(f"❌ '{json_file_path}' is INVALID according to the schema!")
        print(f"\nValidation Error:")
        print(f"  Path: {' -> '.join(str(p) for p in e.absolute_path) if e.absolute_path else 'root'}")
        print(f"  Message: {e.message}")
        
        if e.validator_value:
            print(f"  Expected: {e.validator_value}")
        
        if hasattr(e, 'instance') and e.instance is not None:
            print(f"  Found: {e.instance}")
        
        return False
    
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate JSON files against the red team findings schema",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python validate_json.py competition/results/geb.json
  python validate_json.py my_findings.json competition/samples/findings.schema
        """
    )
    
    parser.add_argument('json_file', 
                       help='Path to the JSON file to validate')
    parser.add_argument('schema_file', 
                       nargs='?',
                       default='competition/samples/findings.schema',
                       help='Path to the schema file (default: competition/samples/findings.schema)')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='Enable verbose output')
    
    args = parser.parse_args()
    
    # Check if files exist
    json_path = Path(args.json_file)
    schema_path = Path(args.schema_file)
    
    if not json_path.exists():
        print(f"Error: JSON file '{args.json_file}' does not exist.")
        sys.exit(1)
    
    if not schema_path.exists():
        print(f"Error: Schema file '{args.schema_file}' does not exist.")
        sys.exit(1)
    
    if args.verbose:
        print(f"Validating: {args.json_file}")
        print(f"Schema: {args.schema_file}")
        print("-" * 50)
    
    # Load files
    json_data = load_json_file(args.json_file)
    schema_data = load_json_file(args.schema_file)
    
    # Validate
    is_valid = validate_json_against_schema(json_data, schema_data, args.json_file)
    
    # Exit with appropriate code
    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()