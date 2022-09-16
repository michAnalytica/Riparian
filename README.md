# Riparian
## Purpose
The purpose of this dataset is to develop a “mask” of the area along tidal and non-tidal connected bodies of water from the edge of the water/land interface inland 30m. The mask includes the water bodies and adjacent land.

## Data and Structure
**Project Folder**
  - **code**
    - run_riparian.py
  - **data**
    - **input**
      - VIMS Chesapeake Bay Shoreline
      - DE Bay Shoreline (derived from 1m CBP LULC 2017/18)
      - FACET (NHD 100k Aligned)
      - Lotic Water and Lakes/Reservoirs (1m CBP LULC 2017/18)
      - **environment**
        - Phase6_Snap.tif
        - Optional: Extent mask
    - **output**
      - riparian_intermediates.gdb (created in the code, holds all intermediate files)
      - riparian_10m.tif (final data)

## How to Execute Code
1. Update and verify paths to the following variables (lines 152-163)
    - folder = “path to main project folder”
    - vims_path = f”{input_folder}/VIMS_FILE_NAME.shp”
    - lotic_path = f”{input_folder}/LOTIC_FILE_NAME.shp”
    - FACET_path = f”{input_folder}/FACET_FILE_NAME.shp”
    - DE_path = f”{input_folder}/DE_SHORELINE_FILE_NAME.shp”
    - extent = f”{input_folder}/environment/EXTENT_FILE_NAME”
      - if you want to run the full extent, extent = “”
2. Save the Script
3. Open the Python Command Prompt and enter: python /path/to_script/run_riparian.py

## Methods
### Shoreline
1. Merge VIMS Chesapeake Bay Shoreline and DE Bay Shoreline
2. Buffer shoreline by 30-meters
3. Erase shoreline from buffered shoreline
    - **Results are part of the final riparian layer**
### High-Resolution Land Use/Land Cover (LULC) Water Classes
1. The lotic water class, where segments are at least 25 acres, and the Lakes and Reservoirs class are buffered by 30-meters
2. The lotic water and lakes are reservoirs are erased from the buffered results
    - **Results are part of the final riparian layer**
### FACET Aligned 1:100k Stream Network
1. Erase the buffered shoreline and LULC water classes from FACET
2. Create a buffer field for remaining FACET streams calculated as: 1/2 of FACET estimated channel width plus 30-meter buffers
3. Buffer FACET streams using buffer field from step 2
    - **Results are part of the final riparian layer**
### Create Final Dataset
1. Merge the 3 riparian datasets into a single vector file
2. Rasterize the merged layer at 10-meters
