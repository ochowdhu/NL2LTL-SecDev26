import csv
import pandas as pd
def load_dataset(file_path):
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        return list(reader)
    
def load_data(data_input):
    """Convert input data to pandas DataFrame."""
    if isinstance(data_input, list):
        return pd.DataFrame(data_input)
    elif isinstance(data_input, str):
        try:
            return pd.read_csv(data_input)
        except Exception as e:
            print(f"Error loading data from file: {str(e)}")
            return None
    else:
        print("Invalid data input. Please provide a list of dictionaries or a file path.")
        return None