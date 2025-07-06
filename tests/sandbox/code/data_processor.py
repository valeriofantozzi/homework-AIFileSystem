import json
import csv
from pathlib import Path

class DataProcessor:
    """A utility class for processing various data formats."""
    
    def __init__(self, data_dir="data/"):
        self.data_dir = Path(data_dir)
        
    def load_json(self, filename):
        """Load JSON data from file."""
        with open(self.data_dir / filename, 'r') as f:
            return json.load(f)
    
    def load_csv(self, filename):
        """Load CSV data as list of dictionaries."""
        data = []
        with open(self.data_dir / filename, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return data
    
    def analyze_performance(self, employee_data):
        """Analyze employee performance metrics."""
        total_score = sum(float(emp['performance_score']) for emp in employee_data)
        avg_score = total_score / len(employee_data)
        
        high_performers = [emp for emp in employee_data 
                          if float(emp['performance_score']) >= 90]
        
        return {
            "average_score": avg_score,
            "high_performers": len(high_performers),
            "total_employees": len(employee_data)
        }
