"""
Script: run_riparian.py
Author: Sarah McDonald, Geographer, USGS: Lower Mississippi-Gulf Water Science Center
        ** Workflow development was led by Renee Thompson, with input from Peter Claggett, Labeeb Ahmed,
            Andy Fitch, and Sarah McDonald. 
Contact: smcdonald@chesapeakebay.net
         rthompso@chesapeakebay.net
Description: This script creates a 10-meter, binary, riparian mask for the specified extent. The riparian zone
             is delineated from four base datasets:
                1. VIMS shoreline
                2. DE Bay Shoreline from CBP 1-meter LULC
                3. FACET aligned 1:100k NHDPlusV2.1 Flowlines
                4. CBP 1-meter resolution land use, lotic water class
            The riparian zone is a 30-meter buffer from the estimated banks of streams, rivers, and other flowing
            water. The mask includes the estimated channels and lotic water, but not the Chesapeake Bay.
How to Run: 1. The user must create the expected folder structure containing the required datasets. The required datasets
               include the 3 list above and the 10-meter Phase6 snap raster. The folder structure is below:
               - main folder (named whatever you want)
                   - code
                       run_riparian.py
                   - data
                       - input
                           VIMS_shoreline
                           DE shoreline
                           FACET
                           Lotic Water
                           - environment
                               Phase6_Snap.tif
                               Optional: extent layer if you want to mask the processing to a subset of the input data
            2. Update the main folder path (folder) to be the path to the main folder above.
            3. Ensure the file names of the vims_path, lotic_path, and FACET_path are correct.
            4. Update the extent variable (extent) to be the name of the extent file. If no extent is being used, set the line to:
                 extent = ""
            5. Save the script
            6. In the search window, search for Python and open the "Python Command Prompt". When it opens, you should see
                a path to ArcGIS Pro Python
            7. in the command prompt type enter python and the path to the script and hit enter. Example entry below:
                    python /main_folder/code/run_riparian.py
"""

import arcpy
import datetime
import os
from sys import argv
from timeit import default_timer as timer

def shoreline(vims_path, DE_path, FACET_path):
    """
    Method: shoreline()
    Purpose: Create riparian zone for shoreline and remove buffered shoreline from FACET.
    Params: vims_path - path to VIMS shoreline
            DE_path - path to DE Bay shoreline
            FACET_path - path to original FACET layer
    Returns: shoreline_riparian - layer name for shoreline riparian area
             facet_erase - layer name for facet with shoreline erased
    """
    # intermediate file names
    buffer = 'shoreline_buffer'
    shoreline = 'shoreline'
    shoreline_riparian = 'shoreline_riparian'
    facet_erase = 'FACET_shoreline_erase'

    # 1. merge shoreline layers
    arcpy.management.Merge(inputs=[vims_path, DE_path], output=shoreline)

    # 2. buffer shoreline
    arcpy.analysis.PairwiseBuffer(in_features=shoreline, out_feature_class=buffer, buffer_distance_or_field="30 Meters", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

    # 3. erase shoreline from buffer
    arcpy.analysis.PairwiseErase(in_features=buffer, erase_features=shoreline, out_feature_class=shoreline_riparian, cluster_tolerance="")

    # 4. Erase buffered shoreline from FACET
    arcpy.analysis.PairwiseErase(in_features=FACET_path, erase_features=buffer, out_feature_class=facet_erase, cluster_tolerance="")

    # return layer names of vims riparian and updated facet
    return shoreline_riparian, facet_erase

def lotic(lotic_path, FACET_shoreline_erase):
    """
    Method: lotic()
    Purpose: Create riparian zones for lotic water and remove lotic from FACET.
    Params: lotic_path - path to lotic water
            FACET_shoreline_erase - layer name for intermediate file with shoreline erased from FACET
    Returns: lotic_riparian - layer name of lotic riparian
             FACET_shoreline_lotic_erase - layer name of FACET with shoreline and lotic erased
    """
    # intermediate layer names
    lotic_buf = 'lotic_buffer'
    lotic_riparian = 'lotic_riparian'
    FACET_shoreline_lotic_erase = "FACET_shoreline_lotic_erase"

    # 1. Buffer lotic water to create lotic riparian zone
    arcpy.analysis.PairwiseBuffer(in_features=lotic_path, out_feature_class=lotic_buf, buffer_distance_or_field="30 Meters", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

    # 2. Remove lotic water from FACET
    arcpy.analysis.PairwiseErase(in_features=FACET_shoreline_erase, erase_features=lotic_path, out_feature_class=FACET_shoreline_lotic_erase, cluster_tolerance="")

    # 3. Remove lotic water from buffered lotic
    arcpy.analysis.PairwiseErase(in_features=lotic_buf, erase_features=lotic_path, out_feature_class=lotic_riparian, cluster_tolerance="")

    # 4. Return layer names for lotic riparian and FACET
    return lotic_riparian, FACET_shoreline_lotic_erase

def FACET(FACET_shoreline_lotic_erase):
    """
    Method: FACET()
    Purpose: Create FACET riparian area
    Params: FACET_shoreline_lotic_erase - FACET layer to be buffered (FACET with shoreline and lotic erased)
    Returns: facet_riparian - layer name of facet riparian
    """
    # intermediate layer names
    facet_riparian = 'FACET_riparian'

    # 1. Create field representing the channel width plus 30-m buffer area
    arcpy.management.CalculateField(in_table=FACET_shoreline_lotic_erase, field="Buffer", expression="(!chnwid_px!/2)+30", expression_type="PYTHON3", code_block="", field_type="TEXT", enforce_domains="NO_ENFORCE_DOMAINS")

    # 2. Buffer FACET
    arcpy.analysis.PairwiseBuffer(in_features=FACET_shoreline_lotic_erase, out_feature_class=facet_riparian, buffer_distance_or_field="Buffer", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

    # 3. Return FACET riparian
    return facet_riparian

def createRiparian(vims_path, lotic_path, FACET_path, DE_path, snap_raster, output_folder, suffix):
    """
    Method: createRiparian()
    Purpose: Create 10-meter raster riparian zones.
    Params: vims_path - path to VIMS shoreline
            lotic_path - path to lotic water
            FACET_path - path to FACET aligned stream network
    Returns: N/A
    """
    # output layer names
    rip_vector = 'riparian_vector'
    riparian_raster = f"{output_folder}/riparian_10m{suffix}.tif"

    # 1. Create shoreline riparian
    print(f"Creating shoreline riparian zone... {datetime.datetime.now()}")
    shoreline_riparian, FACET_shoreline_erase = shoreline(vims_path, DE_path, FACET_path)

    # 2. Create lotic riparian
    print(f"Creating lotic riparian zone...{datetime.datetime.now()}")
    lotic_riparian, FACET_shoreline_lotic_erase = lotic(lotic_path, FACET_shoreline_erase)

    # 3. Create FACET riparian
    print(f"Creating FACET riparian zone...{datetime.datetime.now()}")
    facet_riparian = FACET(FACET_shoreline_lotic_erase)

    # 4. Merge the 3 riparian layers into a single feature layer
    print(f"Merging riparian zones...{datetime.datetime.now()}")
    arcpy.management.Merge(inputs=[shoreline_riparian, lotic_riparian, facet_riparian], output=rip_vector)

    # 5. Create field to rasterize on (all are 1)
    arcpy.management.CalculateField(in_table=rip_vector, field="Raster", expression="1", expression_type="PYTHON3", field_type="SHORT")

    # 6. Rasterize at 10-meters
    print(f"Creating riparian raster mask...{datetime.datetime.now()}")
    arcpy.env.snapRaster = snap_raster
    arcpy.env.compression = "LZW"
    arcpy.PolygonToRaster_conversion(rip_vector, "Raster", riparian_raster, cellsize=snap_raster)


if __name__=="__main__":
    # folder paths
    folder = r'C:/Users/smcdonald/Documents/Data/Riparian' # User updates this line - pass this as argument?
    input_folder = f"{folder}/data/input"
    output_folder = f"{folder}/data/output"

    # file paths
    vims_path = f"{input_folder}/VIMSChesBayShoreline_albers.shp"
    lotic_path = f"{input_folder}/lotic_reservoirs_1m.shp"
    DE_path = f"{input_folder}/DelawareAtlantic_1m_dis.shp"
    FACET_path = f"{input_folder}/FACET_NHD100k_aligned_w_gaps_filled_v1.shp"
    snap_raster = f"{input_folder}/environment/Phase6_Snap.tif"
    
    # optional user entry - path to extent mask
    extent = f"" # test in Patuxent
    suffix = '_MDHWA' # add to end of file names

    # set environment workspace and extent
    arcpy.CreateFileGDB_management(output_folder, f"riparian_intermediates{suffix}.gdb")
    arcpy.env.workspace = f"{output_folder}/riparian_intermediates{suffix}.gdb"
    if os.path.isfile(extent):
        arcpy.env.extent = extent

    # create riparian layer
    st = timer()
    createRiparian(vims_path, lotic_path, FACET_path, DE_path, snap_raster, output_folder, suffix)
    end = round((timer() - st)/60.0, 2)
    print("Run time: {end} minutes")