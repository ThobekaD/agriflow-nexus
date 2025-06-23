import pandas as pd
import os

# Set the path to the folder containing your .xlsx files
# Example for Windows: 'C:\\Users\\YourUsername\\Documents\\ExcelFiles'
# Example for macOS/Linux: '/Users/YourUsername/Documents/ExcelFiles'
# To convert files in the same folder as the script, use '.'
input_folder = 'data/sample' 

# Set the path to the folder where you want to save the .csv files
# To save them in the same folder, use '.'
output_folder = 'data/sample' 

# Create the output folder if it doesn't exist
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Find all .xlsx files in the input folder
for filename in os.listdir(input_folder):
    if filename.endswith('.xlsx'):
        # Construct the full path to the file
        file_path = os.path.join(input_folder, filename)
        
        # Load the Excel file
        try:
            excel_file = pd.ExcelFile(file_path)
            
            # Loop through each sheet in the Excel file
            for sheet_name in excel_file.sheet_names:
                # Read the sheet into a pandas DataFrame
                df = excel_file.parse(sheet_name)
                
                # Create a new name for the CSV file
                # Format: original_filename_sheetname.csv
                base_filename = os.path.splitext(filename)[0]
                csv_filename = f"{base_filename}_{sheet_name}.csv"
                csv_path = os.path.join(output_folder, csv_filename)
                
                # Save the DataFrame to a CSV file
                df.to_csv(csv_path, index=False)
                
                print(f"Successfully converted '{sheet_name}' from '{filename}' to '{csv_filename}'")
                
        except Exception as e:
            print(f"Could not convert {filename}. Error: {e}")

print("\nConversion process finished.")