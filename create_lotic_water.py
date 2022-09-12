import os
import geopandas as gpd 
import pandas as pd

def get_lotic_and_reservoirs(folder, cf, threshold):
    # set path and verify data exists
    lotic_path = f"{folder}/{cf}/input/wetlands/water.gpkg"
    if not os.path.isfile(lotic_path):
        return []

    # read in water for county
    gdf = gpd.read_file(lotic_path, layer='water')

    # select lotic water and reservoirs
    gdf = gdf[['lu_code', 'geometry']]
    gdf.loc[:, 'lu_code'] = gdf.lu_code.astype(int)
    gdf = gdf[gdf['lu_code'].isin([1300, 1210])]

    # remove small lotic water features
    gdf.loc[:, 'acres'] = gdf.geometry.area / 4046.86
    gdf = gdf[(gdf['lu_code']==1210)|((gdf['lu_code']==1300)&(gdf['acres']>=threshold))]
    
    # return lotic water in county
    return gdf[['lu_code','acres','geometry']]

if __name__=="__main__":
    # paths
    folder = r'X:/landuse/version2'
    local_folder = r'C:/Users/smcdonald/Documents/Data/Riparian'
    outpath = f"{local_folder}/data/input/lotic_reservoirs_1m.shp"
    threshold = 25

    # read in lotic polys for each county
    lotic_list = []
    for cf in os.listdir(folder):
        tmp = get_lotic_and_reservoirs(folder, cf, threshold)
        if len(tmp) > 0:
            lotic_list.append(tmp.copy())
            print(f"{cf}: added {len(tmp)} records")
        else:
            print(f"{cf}: no records")
        del tmp

    # concat into one dataframe
    lotic_gdf = pd.concat(lotic_list).pipe(gpd.GeoDataFrame)
    del lotic_list
    lotic_gdf.crs = "EPSG:5070"

    # write results
    lotic_gdf.to_file(outpath)