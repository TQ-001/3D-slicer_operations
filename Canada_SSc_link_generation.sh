#!/bin/bash

# Define directories and files
SRC_DIR="/SAN/medic/ILD/Scans/NIFTI"
DEST_DIR="/SAN/medic/ILD/Scans/Segmentations/nifti_tmp_20260518_SSc"
CSV_FILE="${DEST_DIR}/scl_ids.csv"

# Create the destination directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Check if the CSV file exists before proceeding
if [ ! -f "$CSV_FILE" ]; then
    echo "Error: CSV file not found at $CSV_FILE"
    exit 1
fi

echo "Starting linking process directly from raw NIFTI folder..."

# Read the CSV file, replacing commas with spaces and dropping hidden carriage returns
for patientID in $(tr ',' ' ' < "$CSV_FILE" | tr -d '\r'); do
    
    # Skip any empty lines
    if [ -z "$patientID" ]; then
        continue
    fi
    
    echo "Processing patient: $patientID"
    
    # Define the expected patient folder path
    patient_dir="$SRC_DIR/$patientID"
    
    # 1. Skip the ID if the patient's subfolder doesn't exist in the source directory
    if [ ! -d "$patient_dir" ]; then
        echo "  -> No directory found for $patientID. Skipping."
        continue
    fi
    
    # 2. Iterate recursively through all subfolders for this specific patient
    find "$patient_dir" -type f -name "*.nii.gz" | while read -r filepath; do
        
        # 3. Extract components for the new filename
        # `dirname` gets the folder path containing the file
        # `basename` extracts just the lowest level name (e.g., extracting YYYY-MM-DD from the path)
        raw_date=$(basename "$(dirname "$filepath")")
        orig_filename=$(basename "$filepath")
        
        # Format the date (remove hyphens: YYYY-MM-DD -> YYYYMMDD)
        formatted_date="${raw_date//-/}"
        
        # Extract exact digits from the original filename
        digits=$(echo "$orig_filename" | tr -cd '0-9')
        
        # 4. Construct the properly formatted destination filename
        dest_filename="${patientID}_${formatted_date}_${digits}_0000.nii.gz"
        dest_file="$DEST_DIR/$dest_filename"
        
        # 5. Create the symbolic link
        ln -sf "$filepath" "$dest_file"
        echo "  -> Linked as: $dest_filename"
        
    done

done

echo "Linking operation complete."



# Export filenames to csv
find /SAN/medic/ILD/Scans/Segmentations/nifti_tmp_20260518_SSc/ -type l \
  | sed 's|.*/||' \
  | sed 's/\.[^.]*$//' \
  | sed 's/_0000//g' \
  | sed 's/.nii//g' \
  | awk 'BEGIN { print "filename" } { print "\"" $0 "\"" }' \
  > Canadian_ILD_SSc_QCresults.csv
