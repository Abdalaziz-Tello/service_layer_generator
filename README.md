# Flutter Service Layer Generator

This tool generates a complete service layer for Flutter applications from OpenAPI (Swagger) specifications. It creates type-safe API clients using the Dio package, handles file uploads/downloads, and includes proper error handling.

## Features

- Generates Dart model classes from OpenAPI schemas
- Creates type-safe API service class with Dio integration
- Handles file uploads and downloads
- Includes comprehensive error handling
- Supports all REST API methods (GET, POST, PUT, DELETE, etc.)
- Generates proper null safety support
- Includes timeout and connection error handling
- User-friendly GUI with drag-and-drop support

## Prerequisites

- Python 3.7 or higher
- Flutter SDK
- OpenAPI (Swagger) specification in JSON format

## Installation

1. Clone this repository
2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### GUI Version (Recommended)

Run the GUI version of the generator:
```bash
python service_layer_generator_gui.py
```

The GUI provides:
- Drag-and-drop interface for OpenAPI JSON files
- File browser for selecting input and output locations
- Visual feedback on generation status
- Error messages and success notifications

### Command Line Version

1. Export your OpenAPI specification from Swagger UI as JSON
2. Run the generator:
```bash
python service_layer_generator.py path/to/openapi.json output/directory
```

## Generated Code Structure

The generator will create the following structure:

```
output/
├── models/
│   ├── model1.dart
│   ├── model2.dart
│   └── ...
└── api_service.dart
```

## Flutter Project Setup

1. Add the following dependencies to your `pubspec.yaml`:
```yaml
dependencies:
  dio: ^5.0.0
  json_annotation: ^4.8.1
  path_provider: ^2.0.15

dev_dependencies:
  build_runner: ^2.4.6
  json_serializable: ^6.7.1
```

2. Run the build_runner to generate JSON serialization code:
```bash
flutter pub run build_runner build
```

## Usage in Flutter

```dart
void main() {
  final apiService = ApiService(baseUrl: 'https://api.example.com');
  
  // Example API call
  try {
    final result = await apiService.getUsers();
    print(result);
  } on ApiException catch (e) {
    print('API Error: ${e.message}');
  } on ConnectionException catch (e) {
    print('Connection Error: ${e.message}');
  } on TimeoutException catch (e) {
    print('Timeout Error: ${e.message}');
  }
}

// File upload example
try {
  final file = File('path/to/file');
  final result = await apiService.uploadFileWithFile(
    file: file,
    description: 'My file',
  );
  print(result);
} catch (e) {
  print('Error: $e');
}

// File download example
try {
  await apiService.downloadFile(
    url: 'https://example.com/file.pdf',
    fileName: 'document.pdf',
  );
} catch (e) {
  print('Error: $e');
}
```

## Error Handling

The generated service layer includes comprehensive error handling for:
- API errors (non-200 responses)
- Connection errors
- Timeout errors
- File upload/download errors

## Contributing

Feel free to submit issues and enhancement requests! 