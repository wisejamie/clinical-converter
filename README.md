# clinical-converter

## Overview
The clinical-converter project is designed to convert Clinical Document Architecture (CDA) documents into Fast Healthcare Interoperability Resources (FHIR) format. This project provides a structured approach to handle clinical data transformation, ensuring compatibility with modern healthcare standards.

## Installation
To set up the project, follow these steps:

1. Clone the repository:
   ```
   git clone <repository-url>
   cd clinical-converter
   ```

2. Create a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r backend/requirements.txt
   ```

## Usage
To use the conversion functionality, you can import the `converter` module from the `clinical_converter` package. Here is a basic example:

```python
from clinical_converter.converter import cdaToFhir

# Load your CDA data (e.g., from a file or a string)
cda_data = "<your_cda_data_here>"

# Convert CDA to FHIR
fhir_data = cdaToFhir(cda_data)
print(fhir_data)
```

## Samples
Sample CDA and FHIR documents are provided in the `samples` directory for testing and reference.

## Testing
To run the tests, navigate to the `tests` directory and execute:

```
pytest test_converter.py
```

## Contributing
Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.