import sys
import pandas as pd
import PyPDF2
import re

def analyze_file(file_path, task_description):
    """Analyze file based on task description and return answer"""
    
    if file_path.endswith('.pdf'):
        return analyze_pdf(file_path, task_description)
    elif file_path.endswith(('.csv', '.xlsx', '.xls')):
        return analyze_spreadsheet(file_path, task_description)
    
    return None

def analyze_pdf(file_path, task_description):
    """Extract data from PDF and perform analysis"""
    try:
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract text from specified page or all pages
            page_num = extract_page_number(task_description)
            if page_num and page_num <= len(reader.pages):
                text = reader.pages[page_num - 1].extract_text()
            else:
                text = ' '.join(page.extract_text() for page in reader.pages)
            
            # Look for table data and sum values
            if 'sum' in task_description.lower() and 'value' in task_description.lower():
                return sum_values_from_text(text)
                
    except Exception as e:
        print(f"PDF analysis error: {e}", file=sys.stderr)
    
    return None

def analyze_spreadsheet(file_path, task_description):
    """Analyze CSV/Excel file"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # Sum values in 'value' column if requested
        if 'sum' in task_description.lower() and 'value' in df.columns:
            return int(df['value'].sum())
            
    except Exception as e:
        print(f"Spreadsheet analysis error: {e}", file=sys.stderr)
    
    return None

def extract_page_number(text):
    """Extract page number from task description"""
    match = re.search(r'page\s+(\d+)', text, re.IGNORECASE)
    return int(match.group(1)) if match else None

def sum_values_from_text(text):
    """Extract and sum numeric values from text"""
    # Look for table-like patterns with numbers
    numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
    if numbers:
        return int(sum(float(n) for n in numbers))
    return None

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python analyze.py <file_path> <task_description>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    task_description = sys.argv[2]
    
    result = analyze_file(file_path, task_description)
    if result is not None:
        print(result)
    else:
        print("0")  # Default fallback