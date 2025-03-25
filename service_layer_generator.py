import json
import os
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader
import re
import requests

class ServiceLayerGenerator:
    def __init__(self, openapi_spec_path: str, output_dir: str):
        self.openapi_spec_path = openapi_spec_path
        self.output_dir = output_dir
        self.env = Environment(loader=FileSystemLoader('templates'))
        self.spec = self._load_spec()
        
    def _load_spec(self) -> Dict:
        """Load and validate OpenAPI specification."""
        try:
            # Check if the input is a URL
            if self.openapi_spec_path.startswith(('http://', 'https://')):
                # Handle FastAPI's default Swagger UI URL
                if '/docs' in self.openapi_spec_path:
                    self.openapi_spec_path = self.openapi_spec_path.replace('/docs', '/openapi.json')
                elif not self.openapi_spec_path.endswith('.json'):
                    self.openapi_spec_path = self.openapi_spec_path.rstrip('/') + '/openapi.json'
                
                print(f"Fetching OpenAPI spec from: {self.openapi_spec_path}")
                response = requests.get(self.openapi_spec_path)
                response.raise_for_status()
                
                # Print response headers and content type for debugging
                print(f"Response headers: {dict(response.headers)}")
                print(f"Content type: {response.headers.get('content-type', 'unknown')}")
                
                # Try to decode the response content
                try:
                    content = response.text
                    print(f"Response content preview: {content[:1000]}...")  # Print first 1000 chars
                    spec = json.loads(content)
                except json.JSONDecodeError as e:
                    print(f"JSON decode error at line {e.lineno}, column {e.colno}")
                    print(f"Error message: {str(e)}")
                    print(f"Response content: {content[:2000]}...")  # Print first 2000 chars for debugging
                    raise Exception(f"Invalid JSON response from URL: {str(e)}")
            else:
                with open(self.openapi_spec_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"File content preview: {content[:1000]}...")  # Print first 1000 chars
                    try:
                        spec = json.loads(content)
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error at line {e.lineno}, column {e.colno}")
                        print(f"Error message: {str(e)}")
                        print(f"File content: {content[:2000]}...")  # Print first 2000 chars for debugging
                        raise Exception(f"Invalid JSON in file: {str(e)}")

            # Handle different OpenAPI versions
            version = spec.get('openapi') or spec.get('swagger')
            
            if version:
                print(f"Detected OpenAPI/Swagger version: {version}")
                # OpenAPI 3.x or Swagger 2.x
                return spec
            else:
                # Try to detect if it's a FastAPI Swagger UI response
                if isinstance(spec, dict) and 'paths' in spec:
                    print("Detected FastAPI Swagger format")
                    return spec
                else:
                    print(f"Available keys in spec: {list(spec.keys())}")
                    raise Exception(f"Unsupported OpenAPI/Swagger format. Spec keys: {list(spec.keys())}")

        except requests.exceptions.RequestException as e:
            print(f"Request error: {str(e)}")
            raise Exception(f"Failed to fetch OpenAPI spec from URL: {str(e)}")
        except Exception as e:
            print(f"General error: {str(e)}")
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
            
        # Handle references
        if '$ref' in schema:
            ref_path = schema['$ref'].split('/')
            ref_name = ref_path[-1]
            return self._sanitize_name(ref_name)
            
        type_mapping = {
            'string': 'String',
            'integer': 'int',
            'number': 'double',
            'boolean': 'bool',
            'array': 'List',
            'object': 'Map<String, dynamic>',
        }
        
        # Handle nullable types
        if schema.get('nullable', False):
            base_type = schema.get('type', 'object')
            dart_type = type_mapping.get(base_type, 'dynamic')
            return f'{dart_type}?'
        
        base_type = schema.get('type', 'object')
        dart_type = type_mapping.get(base_type, 'dynamic')
        
        if base_type == 'array':
            items = schema.get('items', {})
            item_type = self._get_dart_type(items)
            return f'List<{item_type}>'
            
        return dart_type

    def _generate_model_class(self, name: str, schema: Dict, is_request: bool = False) -> str:
        """Generate Dart model class from schema."""
        # Handle references
        if '$ref' in schema:
            ref_path = schema['$ref'].split('/')
            ref_name = ref_path[-1]
            return self._generate_model_class(ref_name, self._resolve_reference(ref_path), is_request)
            
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

    def _generate_request_model(self, operation: Dict, path: str, method: str) -> str:
        """Generate request model for an operation."""
        request_body = operation.get('requestBody', {})
        if not request_body:
            return 'dynamic'
            
        content = request_body.get('content', {})
        schema = content.get('application/json', {}).get('schema', {})
        
        if not schema:
            return 'dynamic'
            
        # Generate a unique name for the request model
        model_name = f"{method.upper()}{self._sanitize_name(path)}Request"
        model_content = self._generate_model_class(model_name, schema, True)
        
        # Save the model file
        models_dir = os.path.join(self.output_dir, 'models')
        model_file = os.path.join(models_dir, f"{model_name}.dart")
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(model_content)
            
        return model_name

    def _generate_response_model(self, operation: Dict, path: str, method: str) -> str:
        """Generate response model for an operation."""
        responses = operation.get('responses', {})
        success_response = responses.get('200', {})
        content = success_response.get('content', {})
        schema = content.get('application/json', {}).get('schema', {})
        
        if not schema:
            return 'dynamic'
            
        # Generate a unique name for the response model
        model_name = f"{method.upper()}{self._sanitize_name(path)}Response"
        model_content = self._generate_model_class(model_name, schema, False)
        
        # Save the model file
        models_dir = os.path.join(self.output_dir, 'models')
        model_file = os.path.join(models_dir, f"{model_name}.dart")
        with open(model_file, 'w', encoding='utf-8') as f:
            f.write(model_content)
            
        return model_name

    def _generate_api_service(self, paths: Dict) -> str:
        """Generate Dart API service class."""
        endpoints = []
        
        for path, methods in paths.items():
            for method, operation in methods.items():
                operation_id = operation.get('operationId', '')
                parameters = operation.get('parameters', [])
                
                # Generate request and response models
                request_model = self._generate_request_model(operation, path, method)
                response_model = self._generate_response_model(operation, path, method)
                
                endpoints.append({
                    'path': path,
                    'method': method.upper(),
                    'name': self._sanitize_name(operation_id or f"{method}_{path}"),
                    'parameters': parameters,
                    'request_model': request_model,
                    'response_model': response_model,
                    'has_file': self._has_file_parameter(parameters, operation.get('requestBody', {}))
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
        
        # Generate models directory
        models_dir = os.path.join(self.output_dir, 'models')
        os.makedirs(models_dir, exist_ok=True)
        
        # Generate API service
        api_service_content = self._generate_api_service(self.spec.get('paths', {}))
        api_service_file = os.path.join(self.output_dir, 'api_service.dart')
        with open(api_service_file, 'w', encoding='utf-8') as f:
            f.write(api_service_content)

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate Dart service layer from OpenAPI spec')
    parser.add_argument('openapi_spec', help='Path to OpenAPI specification JSON file or URL')
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