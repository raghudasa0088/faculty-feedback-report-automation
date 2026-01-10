# Faculty Feedback Report Automation

This repository contains a Python-based automation tool that converts raw faculty feedback data from Excel into a structured, visual PDF report.

## What it does
- Reads faculty feedback data from an Excel file
- Computes weighted averages and overall scores
- Generates response distribution charts
- Produces a clean, two-page PDF report with quantitative analysis and qualitative comments

## Requirements
- Python 3.8+
- pandas
- numpy
- matplotlib
- fpdf2
- openpyxl

## Installation
```bash
pip install pandas numpy matplotlib fpdf2 openpyxl
```

## Usage
1. Place your feedback Excel file in the project directory.
2. Update the `EXCEL_FILE` variable in `generate_report.py` with the file name.
3. Run:
```bash
python generate_report.py
```
4. The PDF report will be generated in the same directory.

## Notes
- The script auto-detects the faculty name from the Excel file name.
- Designed for institutional feedback formats with Likert-scale responses.

## License
MIT
