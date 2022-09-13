import os
import geopandas as gpd 
import pandas as pd
import multiprocessing as mp

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

def remove_disconnected_features(facet_path, lotic_gdf):
    """
    Method: remove_disconnected_features()
    Purpose: Intersect the lotic and reservoirs data with FACET to remove ponds, lakes,
             and other features not connected to the stream network.
    Params: facet_path - path to FACET streams
            lotic_gdf - geodataframe of lotic water and reservoirs from LULC
    Returns: lotic_gdf
    """
    # 1. read in FACET streams
    facet = gpd.read_file(facet_path, bbox=lotic_gdf.envelope)

    # 2. Get list of lotic features that intersect FACET
    lotic_gdf.loc[:, 'id'] = [int(x) for x in range(len(lotic_gdf))]
    lotic_ids = sjoin_mp(lotic_gdf[['id','geometry']], 'intersects', facet[['geometry']])
    del facet

    # 3. select lotic features intersecting facet
    print(f"Removing {len(lotic_gdf) - len(lotic_ids)} disconnected features")
    lotic_gdf = lotic_gdf[lotic_gdf['id'].isin(lotic_ids)]
    del lotic_ids

    return lotic_gdf

def sjoin_mp(df1, sjoin_op, df2):
    """
    Method: sjoin_mp6()
    Purpose: Chunk and mp a sjoin function on specified geodataframes for specified operation,
             retaining specified columns.
    Params: df1 - geodataframe of data to chunk and sjoin (left gdf)
            batch_size - integer value of max number of records to include in each chunk
            sjoin_op - string of sjoin operation to use; 'intersects', 'within', 'contains'
            sjoinCols - list of column names to retain
            df2 - geodataframe of data to sjoin (right gdf)
    Returns: sjoinSeg - df (or gdf) of sjoined data, with sjoin columns retained
    """
    NUM_CPUS, batch_size = 6, (int(len(df1) / 6) + 1)
    print(f"{NUM_CPUS} batches of {batch_size} for {len(df1)} records")
 
    chunk_iterator = []
    for i in range(NUM_CPUS):
        mn, mx = i * batch_size, (i + 1) * batch_size
        gdf_args = df1[mn:mx], df2, sjoin_op
        chunk_iterator.append(gdf_args)

    pool = mp.Pool(processes=NUM_CPUS)
    sj_results = pool.map(sjoin, chunk_iterator)
    pool.close()
    sj_results = sum(sj_results, [])
    return sj_results

def sjoin(args):
    """
    Method: sjoin_mp_pt5()
    Purpose: Run sjoin on specified geodataframes for specified operation,
             retaining specified columns.
    Params: args - tuple of arguments
                df1 - geodataframe of data to sjoin (left gdf)
                df2 - geodataframe of data to sjoin (right gdf)
                sjoin_op - string of sjoin operation to use; 'intersects', 'within', 'contains'
                sjoinCols - string of column names to retain, separated by a space
    Returns: sjoinSeg - df (or gdf) of sjoined data, with sjoin columns retained
    """
    df1, df2, sjoin_op = args 
    sjoinSeg = gpd.sjoin(df1, df2, how='inner', op=sjoin_op)
    sjoinSeg.drop_duplicates(inplace=True)
    return list(sjoinSeg['id'])

if __name__=="__main__":
    # paths
    folder = r'X:/landuse/version2'
    local_folder = r'C:/Users/smcdonald/Documents/Data/Riparian'
    facet_path = f"{local_folder}/data/input/FACET_NHD100k_aligned_w_gaps_filled_v1.shp"
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

    # test only
    lotic_gdf = gpd.read_file(outpath)

    # remove features not connected to the stream network
    lotic_gdf = remove_disconnected_features(facet_path, lotic_gdf)

    # write results
    lotic_gdf.to_file(outpath)