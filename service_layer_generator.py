import json
import os
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader
import re

class ServiceLayerGenerator:
    def __init__(self, openapi_spec_path: str, output_dir: str):
        self.openapi_spec_path = openapi_spec_path
        self.output_dir = output_dir
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.spec = self._load_spec()
        
    def _load_spec(self) -> Dict:
        """Load and validate OpenAPI specification."""
        try:
            with open(self.openapi_spec_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"Failed to load OpenAPI spec: {str(e)}")

    def _sanitize_name(self, name: str) -> str:
        """Convert string to valid Dart identifier."""
        # Remove special characters and spaces
        name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        # Ensure it starts with a letter
        if not name[0].isalpha():
            name = 'a' + name
        return name

    def _get_dart_type(self, schema: Dict) -> str:
        """Convert OpenAPI schema to Dart type."""
        if not schema:
            return 'dynamic'
            
        type_mapping = {
            'string': 'String',
            'integer': 'int',
            'number': 'double',
            'boolean': 'bool',
            'array': 'List',
            'object': 'Map<String, dynamic>',
        }
        
        base_type = schema.get('type', 'object')
        dart_type = type_mapping.get(base_type, 'dynamic')
        
        if base_type == 'array':
            items = schema.get('items', {})
            item_type = self._get_dart_type(items)
            return f'List<{item_type}>'
            
        return dart_type

    def _generate_model_class(self, name: str, schema: Dict) -> str:
        """Generate Dart model class from schema."""
        properties = schema.get('properties', {})
        required = schema.get('required', [])
        
        fields = []
        for prop_name, prop_schema in properties.items():
            dart_type = self._get_dart_type(prop_schema)
            is_required = prop_name in required
            fields.append({
                'name': self._sanitize_name(prop_name),
                'type': dart_type,
                'required': is_required
            })
            
        template = self.env.get_template('model.dart.j2')
        return template.render(
            class_name=self._sanitize_name(name),
            fields=fields
        )

    def _generate_api_service(self, paths: Dict) -> str:
        """Generate Dart API service class."""
        endpoints = []
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                operation_id = operation.get('operationId', '')
                parameters = operation.get('parameters', [])
                request_body = operation.get('requestBody', {})
                responses = operation.get('responses', {})
                
                # Get response type
                success_response = responses.get('200', {})
                response_schema = success_response.get('content', {}).get('application/json', {}).get('schema', {})
                response_type = self._get_dart_type(response_schema)
                
                # Get request body type
                request_schema = request_body.get('content', {}).get('application/json', {}).get('schema', {})
                request_type = self._get_dart_type(request_schema)
                
                endpoints.append({
                    'path': path,
                    'method': method.upper(),
                    'name': self._sanitize_name(operation_id or f"{method}_{path}"),
                    'parameters': parameters,
                    'request_type': request_type,
                    'response_type': response_type,
                    'has_file': self._has_file_parameter(parameters, request_body)
                })
                
        template = self.env.get_template('api_service.dart.j2')
        return template.render(endpoints=endpoints)

    def _has_file_parameter(self, parameters: List, request_body: Dict) -> bool:
        """Check if endpoint has file upload/download."""
        for param in parameters:
            if param.get('in') == 'formData' and param.get('type') == 'file':
                return True
                
        if request_body.get('content', {}).get('multipart/form-data'):
            return True
            
        return False

    def generate(self):
        """Generate all necessary Dart files."""
        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate models
        models_dir = os.path.join(self.output_dir, 'models')
        os.makedirs(models_dir, exist_ok=True)
        
        schemas = self.spec.get('components', {}).get('schemas', {})
        for name, schema in schemas.items():
            model_content = self._generate_model_class(name, schema)
            model_file = os.path.join(models_dir, f"{self._sanitize_name(name)}.dart")
            with open(model_file, 'w', encoding='utf-8') as f:
                f.write(model_content)
        
        # Generate API service
        api_service_content = self._generate_api_service(self.spec.get('paths', {}))
        api_service_file = os.path.join(self.output_dir, 'api_service.dart')
        with open(api_service_file, 'w', encoding='utf-8') as f:
            f.write(api_service_content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate Dart service layer from OpenAPI spec')
    parser.add_argument('openapi_spec', help='Path to OpenAPI specification JSON file')
    parser.add_argument('output_dir', help='Output directory for generated Dart files')
    
    args = parser.parse_args()
    
    try:
        generator = ServiceLayerGenerator(args.openapi_spec, args.output_dir)
        generator.generate()
        print(f"Successfully generated Dart service layer in {args.output_dir}")
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)

if __name__ == '__main__':
    main() 