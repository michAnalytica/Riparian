"""
Script: run_riparian.py
Author: Sarah McDonald, Geographer, USGS: Lower Mississippi-Gulf Water Science Center
        ** Workflow development was led by Renee Thompson, with input from Peter Claggett, Labeeb Ahmed,
            Andy Fitch, and Sarah McDonald. 
Contact: smcdonald@chesapeakebay.net
         rthompso@chesapeakebay.net
Update: 
              - Buffer method updated from GEODESIC to PLANAR
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
from arcpy.sa import *
import datetime
import os
from sys import argv
from timeit import default_timer as timer

def time_dif(st_time):
    cur = timer()
    end = round((cur - st_time)/60.0, 2)
    print(f"\tRun time: {end} minutes")
    return cur

def shoreline(vims_path, DE_path, FACET_data, huc_mask, buffer_width):
    """
    Method: shoreline()
    Purpose: Create riparian zone for shoreline and remove buffered shoreline from FACET.
    Params: vims_path - path to VIMS shoreline
            DE_path - path to DE Bay shoreline
            FACET - path to original FACET layer
    Returns: shoreline_riparian - layer name for shoreline riparian area
             facet_erase - layer name for facet with shoreline erased
    """
    # intermediate file names
    buffer = 'shoreline_buffer'
    shoreline = 'shoreline'
    shoreline_riparian = 'shoreline_riparian'
    vims_clip = 'VIMS_clip'
    de_clip = 'DE_clip'
    facet_erase = 'FACET_shoreline_erase'

    # 1. merge shoreline layers
    if not arcpy.Exists(f"{arcpy.env.workspace}/{shoreline}"):
        # clip layers to huc
        if int(arcpy.GetCount_management(vims_path).getOutput(0)) > 0:
            arcpy.analysis.Clip(vims_path, huc_mask, vims_clip)
        if int(arcpy.GetCount_management(DE_path).getOutput(0)) > 0:
            arcpy.analysis.Clip(DE_path, huc_mask, de_clip)

        # merge shoreline
        if  arcpy.Exists(f"{arcpy.env.workspace}/{vims_clip}") and arcpy.Exists(f"{arcpy.env.workspace}/{de_clip}"):
            arcpy.management.Merge(inputs=[vims_clip, de_clip], output=shoreline)
        elif arcpy.Exists(f"{arcpy.env.workspace}/{vims_clip}"):
            arcpy.management.CopyFeatures(vims_clip, shoreline)
        elif arcpy.Exists(f"{arcpy.env.workspace}/{de_clip}"):
            arcpy.management.CopyFeatures(de_clip, shoreline)
        else: # no shoreline - just copy FACET and return
            print("\t\tNo shoreline for HUC")
            if not arcpy.Exists(f"{arcpy.env.workspace}/{facet_erase}"):
                arcpy.management.CopyFeatures(FACET_data, facet_erase)
            return shoreline_riparian, facet_erase

    # 2. buffer shoreline
    if not arcpy.Exists(f"{arcpy.env.workspace}/{buffer}"):
        arcpy.analysis.PairwiseBuffer(in_features=shoreline, out_feature_class=buffer, buffer_distance_or_field=f"{buffer_width} Meters", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

    # 3. erase shoreline from buffer
    if not arcpy.Exists(f"{arcpy.env.workspace}/{shoreline_riparian}"):
        arcpy.analysis.PairwiseErase(in_features=buffer, erase_features=shoreline, out_feature_class=shoreline_riparian, cluster_tolerance="")

    # 4. erase shoreline buffer from FACET
    if not arcpy.Exists(f"{arcpy.env.workspace}/{facet_erase}"):
        arcpy.analysis.PairwiseErase(in_features=FACET_data, erase_features=buffer, out_feature_class=facet_erase, cluster_tolerance="")

    # return layer names of vims riparian and updated facet
    return shoreline_riparian, facet_erase

def lotic(lotic_path, FACET_shoreline_erase, buffer_width):
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

    # validate records exist
    cnt = int(arcpy.GetCount_management(lotic_path).getOutput(0))
    if cnt > 0:
        # 1. Buffer lotic water to create lotic riparian zone
        if not arcpy.Exists(f"{arcpy.env.workspace}/{lotic_buf}"):
            arcpy.analysis.PairwiseBuffer(in_features=lotic_path, out_feature_class=lotic_buf, buffer_distance_or_field=f"{buffer_width} Meters", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

        # 2. Remove lotic water from FACET
        if not arcpy.Exists(f"{arcpy.env.workspace}/{FACET_shoreline_lotic_erase}"):
            arcpy.analysis.PairwiseErase(in_features=FACET_shoreline_erase, erase_features=lotic_path, out_feature_class=FACET_shoreline_lotic_erase, cluster_tolerance="")

        # 3. Remove lotic water from buffered lotic
        if not arcpy.Exists(f"{arcpy.env.workspace}/{lotic_riparian}"):
            arcpy.analysis.PairwiseErase(in_features=lotic_buf, erase_features=lotic_path, out_feature_class=lotic_riparian, cluster_tolerance="")
    else:
        print("\t\tNo lotic in HUC")
        arcpy.management.CopyFeatures(FACET_shoreline_erase, FACET_shoreline_lotic_erase)

    # 4. Return layer names for lotic riparian and FACET
    return lotic_riparian, FACET_shoreline_lotic_erase

def FACET(FACET_shoreline_lotic_erase, buffer_width):
    """
    Method: FACET()
    Purpose: Create FACET riparian area
    Params: FACET_shoreline_lotic_erase - FACET layer to be buffered (FACET with shoreline and lotic erased)
    Returns: facet_riparian - layer name of facet riparian
    """
    # intermediate layer names
    facet_riparian = 'FACET_riparian'

    if not arcpy.Exists(f"{arcpy.env.workspace}/{facet_riparian}"): 
        # 1. Create field representing the channel width plus 30-m buffer area
        lstFields = arcpy.ListFields(FACET_shoreline_lotic_erase)
        lstFields = [field.name for field in lstFields]
        buf_field = "Buffer"
        if "Buffer" not in lstFields and "buffer" not in lstFields:
            arcpy.AddField_management(FACET_shoreline_lotic_erase, 'Buffer', "DOUBLE" ) # need this to avoid database lock error ?

        arcpy.management.CalculateField(in_table=FACET_shoreline_lotic_erase, field="Buffer", expression=f"(!chnwid_px!/2)+{buffer_width}", expression_type="PYTHON3", code_block="", field_type="TEXT", enforce_domains="NO_ENFORCE_DOMAINS")

        # 2. Buffer FACET
        arcpy.analysis.PairwiseBuffer(in_features=FACET_shoreline_lotic_erase, out_feature_class=facet_riparian, buffer_distance_or_field="Buffer", dissolve_option="ALL", dissolve_field=[], method="GEODESIC", max_deviation="0 Meters")

    # 3. Return FACET riparian
    return facet_riparian

def createRiparian(vims_path, lotic_path, FACET_data, DE_path, snap_raster, mask_raster, output_folder, suffix, huc_extent, buffer_width):
    """
    Method: createRiparian()
    Purpose: Create 10-meter raster riparian zones.
    Params: vims_path - path to VIMS shoreline
            lotic_path - path to lotic water
            FACET - path to FACET aligned stream network
    Returns: N/A
    """
    # output layer names
    rip_vector = 'riparian_vector'
    riparian_raster_tmp = f"{output_folder}/riparian_10m{suffix}_unmasked.tif"
    riparian_raster = f"{output_folder}/riparian_10m{suffix}.tif"
    if not mask_raster:
        riparian_raster_tmp = riparian_raster

    st = timer()
    # 1. Create shoreline riparian
    print(f"\tCreating shoreline riparian zone... {datetime.datetime.now()}")
    shoreline_riparian, FACET_shoreline_erase = shoreline(vims_path, DE_path, FACET_data, huc_extent, buffer_width)
    st = time_dif(st)

    # 2. Create lotic riparian
    print(f"\tCreating lotic riparian zone...{datetime.datetime.now()}")
    lotic_riparian, FACET_shoreline_lotic_erase = lotic(lotic_path, FACET_shoreline_erase, buffer_width)
    st = time_dif(st)

    # 3. Create FACET riparian
    print(f"\tCreating FACET riparian zone...{datetime.datetime.now()}")
    facet_riparian = FACET(FACET_shoreline_lotic_erase, buffer_width)
    st = time_dif(st)

    # 4. Merge the 3 riparian layers into a single feature layer
    try:
        shoreline_cnt = int(arcpy.GetCount_management(shoreline_riparian).getOutput(0))
    except:
        shoreline_cnt = 0
    try:
        lotic_cnt = int(arcpy.GetCount_management(lotic_riparian).getOutput(0))
    except:
        lotic_cnt = 0      
    if shoreline_cnt == 0 and lotic_cnt == 0:
        in_table = facet_riparian
    else:
        if not arcpy.Exists(f"{arcpy.env.workspace}/{rip_vector}"): 
            inputs = [facet_riparian]
            if shoreline_cnt > 0:
                inputs.append(shoreline_riparian)
            if lotic_cnt > 0:
                inputs.append(lotic_riparian)
            print(f"\tMerging riparian zones...{datetime.datetime.now()}")
            arcpy.management.Merge(inputs=inputs, output=rip_vector)
            in_table = rip_vector
            st = time_dif(st)

    # 5. Create field to rasterize on (all are 1)
    if "Raster" not in [field.name for field in arcpy.ListFields(in_table)]:
        arcpy.management.CalculateField(in_table=in_table, field="Raster", expression="1", expression_type="PYTHON3", field_type="SHORT")

    # 6. Rasterize at 10-meters
    print(f"\tCreating riparian raster ...{datetime.datetime.now()}")
    arcpy.env.snapRaster = snap_raster
    arcpy.env.compression = "LZW"
    arcpy.PolygonToRaster_conversion(rip_vector, "Raster", riparian_raster_tmp, cellsize=snap_raster)
    st = time_dif(st)

    # 7. extract riparian by mask
    if mask_raster and len(hucs) == 1: # if more than one huc, impose mask after mosaic
        ras = ExtractByMask(riparian_raster_tmp, mask_raster)
        arcpy.env.snapRaster = snap_raster
        arcpy.env.compression = "LZW"
        arcpy.management.CopyRaster(ras, 
                                    riparian_raster, 
                                    background_value=0, 
                                    nodata_value=0,
                                    pixel_type='1_BIT', 
                                    format="TIFF")


if __name__=="__main__":
    # folder paths
    folder = r'C:/Users/smcdonald/Documents/Riparian24k' # User updates this line - pass this as argument?
    input_folder = f"{folder}/data/input"
    output_folder = f"{folder}/data/output/35ft"
    huc8_folder = f"{input_folder}/environment/huc8s"
    huc_output = f"{output_folder}/huc8"
    print(output_folder)

    # file paths
    vims_path = f"{input_folder}/VIMSChesBayShoreline_albers.shp"
    lotic_path = f"{input_folder}/lotic_reservoirs_1m_24k_CBW.shp"
    DE_path = f"{input_folder}/DE-shoreline_LULC-NOAASLR0ft_albers.shp"
    FACET_path = f"{input_folder}/facet_plus_nhd_24k.gdb"
    facet_layer='facet_plus_nhd_24k_CopyFeatures'
    snap_raster = f"{input_folder}/environment/Phase6_Snap.tif"
    hucs = [x for x in os.listdir(huc8_folder) if x[-3:]=='shp']

    # buffer width in meters
    buffer_width = 10
    print(f"Buffer width: {buffer_width}\n\n")
    
    # optional user entry - path to extent mask
    mask = f"{input_folder}/environment/CBW_NHDv21_catchment_albers_30m_2022.tif" # CBW
    huc_ras_list = []
    for huc in hucs: # subset - FACET layer too large to run for region
        extent = f"{huc8_folder}/{huc}"
        suffix = f'_{huc.split(".")[0]}' # add to end of file names
        riparian_raster = f"{huc_output}/riparian_10m{suffix}_unmasked.tif"

        print(f"\n{suffix}: {(hucs.index(huc)+1)} of {len(hucs)}")
        if os.path.isfile(riparian_raster):
            print(f"\tRiparian is complete - skipping")
            huc_ras_list.append(riparian_raster)
            continue

        # set environment workspace and extent
        try:
            arcpy.CreateFileGDB_management(huc_output, f"riparian_intermediates{suffix}.gdb")
        except:
            print("WARNING: Geodatabase already exists. Overwriting contents.")
            arcpy.env.overwriteOutput = True
            # continue

        # subset FACET data
        arcpy.env.workspace = FACET_path
        facet_selection = arcpy.management.SelectLayerByLocation(facet_layer, "INTERSECT", extent)

        # set output gdb as workspace
        arcpy.env.workspace = f"{huc_output}/riparian_intermediates{suffix}.gdb"
        if os.path.isfile(extent):
            arcpy.env.extent = extent # set extent to huc8

        # create riparian layer
        st = timer()
        try:
            createRiparian(vims_path, lotic_path, facet_selection, DE_path, snap_raster, mask, huc_output, suffix, extent, buffer_width)
            huc_ras_list.append(riparian_raster)
        except Exception as e:
            print(f"ERROR: createRiparian failed for {suffix}/n{e}/n/n")
        time_dif(st)

        arcpy.env.extent = None

    print("\nAll Hucs Complete")

    # add step to mosaic tiffs - max value takes precedence
    if not os.path.isfile(f"{output_folder}/CBW_riparian_24k_unmasked_2023.tif"):
        huc_ras_list = [Raster(rasPath) for rasPath in huc_ras_list]
        arcpy.env.compression = "LZW"
        print(f"\n\nMosaicking {len(huc_ras_list)} huc rasters")
        arcpy.management.MosaicToNewRaster(huc_ras_list, output_folder, "CBW_riparian_24k_unmasked_2023.tif", pixel_type="1_BIT", cellsize=10.0, number_of_bands=1, mosaic_method="MAXIMUM")

    # add step to remove shorelines - new workflow clips shoreline by huc resulting is false buffers in the estuary
    vims_ras = f"{input_folder}/vims_10m.tif"
    de_ras = f"{input_folder}/de_10m.tif"
    arcpy.env.snapRaster = snap_raster
    arcpy.env.compression = "LZW"

    if not os.path.isfile(vims_ras):
        print(f"Rasterizing VIMS ...{datetime.datetime.now()}")
        arcpy.PolygonToRaster_conversion(vims_path, "Raster", vims_ras, cellsize=snap_raster)

    if not os.path.isfile(de_ras):
        print(f"Rasterizing DE Shoreline ...{datetime.datetime.now()}")
        arcpy.PolygonToRaster_conversion(DE_path, "Id", de_ras, cellsize=snap_raster)

    if not os.path.isfile(f"{output_folder}/CBW_riparian_{buffer_width}m_24k_2023.tif"):
        arcpy.env.extent = mask
        arcpy.env.mask = mask
        ras = Raster(f"{output_folder}/CBW_riparian_24k_unmasked_2023.tif")
        vims = Con(IsNull(Raster(vims_ras)), 0, 1)
        de = Con(IsNull(Raster(de_ras)), 0, 1)
        ras = Con(( ( vims == 1) | (de == 1) ),0,ras)
        del vims
        del de

        # # mask mosaicked results
        # print("Masking CBW dataset")
        # ras = ExtractByMask(ras, mask)
        arcpy.env.snapRaster = snap_raster
        arcpy.env.compression = "LZW"
        arcpy.env.extent = mask
        print("Writing riparian layer")
        arcpy.management.CopyRaster(ras, 
                                    f"{output_folder}/CBW_riparian_{buffer_width}m_24k_2023.tif", 
                                    background_value=0, 
                                    nodata_value=0,
                                    pixel_type='1_BIT', 
                                    format="TIFF")
        del ras
