import sys
sys.path.append('/mnt/entsoc2024-efs/lib')
import json
import shutil
import urllib
import os
import zipfile
import boto3
from degree_day import degree_day as dd
import xarray as xra
import rioxarray
import matplotlib.pyplot as plt
import geopandas as gpd


def lambda_handler(event, context):
   
    # Test connection to internet 
    print('Testing internet connection...')
    try:
        response = urllib.request.urlopen('https://aws.amazon.com')
        status_code = response.getcode()
        print(f'- Response Code: {status_code}. Internet connection established!')
    except Exception as e:
        print('- Error:', e)
        raise e

    print("Loading Common Variables and Objects")
    ## Common objects
    weather_var_list = ['tmin', 'tmax'] 
    base_url = 'https://services.nacse.org/prism/data/public/4km'
    format = 'nc'
    s3_bucket = 'entsoc2024-ecodata-cloud-workshop'
    s3_client = boto3.client('s3')

    # event parameters 
    if 'queryStringParameters' in event:
        event = event['queryStringParameters']
    target_date = event['date']
    lt = int(event['temp_low'])
    ut = int(event['temp_high'])
    user = event['user']
    state = event['state']
    
    # paths
    storage_dir = "/tmp/prism-etl" # for lambda 
    gdd_dir = os.path.join(storage_dir, 'gdd')
    if os.path.exists(gdd_dir):
        shutil.rmtree(gdd_dir)
    os.makedirs(gdd_dir)
    raster_name = f'gdd_raster_user={user}_date={target_date}_lt={lt}_ut={ut}.nc'
    local_raster_path = os.path.join(gdd_dir, raster_name)
    png_name = f'gdd_raster_user={user}_date={target_date}_lt={lt}_ut={ut}.png'
    local_png_path = os.path.join(gdd_dir, png_name)
    s3_raster_loc = f'gdd_rasters/{user}/{raster_name}'
    s3_png_loc = f'gdd_rasters/{user}/{png_name}'
        

    print(f"Pulling weather data from PRISM for {target_date}.")
    for var in weather_var_list:
        dest_dir = os.path.join(storage_dir, var, target_date)
        dest_file = os.path.join(dest_dir, f'{var}_{target_date}.zip')
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # download data
        url =f'{base_url}/{var}/{target_date}?format={format}'
        print(f'- Requesting {var} at {url}')

        # handle failed connection to PRISM server
        try:
            urllib.request.urlretrieve(url, dest_file)
        except: 
            print('- Failed connection to PRISM!')
            break 
        else: print('- Connection to PRISM endpoint established.')
        
        # test for successful weather pull by checking for zip file 
        iszip = zipfile.is_zipfile(dest_file)
        if not iszip: 
            weather_pull_succeeded = False
            print(f'- Weather data for {var} failed to pull!') 
            break # need both tmin and tmax, so break out if either fails

        # unzip data
        print(f'- Uncompressing {var} download')
        with zipfile.ZipFile(dest_file, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        
        print(f'- Successfully pulled {var}')
        
    # Load PRISM rasters and clip to state
    print(f'Loading PRISM rasters and clipping to {state}.') 
    prism_dict = {} 
    shp = gpd.read_file(f'zip+s3://entsoc2024-ecodata-cloud-workshop/tl_2024_us_state.zip')
    # shp = gpd.read_file('/mnt/ecodata2024-efs/tl_2024_us_state.zip')
    shp_state = shp.loc[lambda x: x.NAME == state]
    for var in ['tmin', 'tmax']:
        print(f'- Clipping {var} raster.')
        # load var
        dest_dir = os.path.join(storage_dir, var, target_date)
        file_name = f'PRISM_{var}_stable_4kmD2_{target_date}_nc.nc'
        file_path = os.path.join(dest_dir, file_name)
        raw_raster = rioxarray.open_rasterio(file_path)
        or_raster = raw_raster.rio.clip(shp_state.geometry, drop = True)
        or_raster = or_raster.where(or_raster != -9999)
        prism_dict[var] = or_raster.drop_vars('band').squeeze()
        del raw_raster, or_raster

    # create GDD artifacts
    print('Creating GDD artifacts.')

    # get gdd layer
    print(f'- Setting up degree day calculator with lt = {lt} and ut = {ut}')
    ss_calculator = dd.DegreeDayCalculator(lt, ut) 

    print(f'- Calculating raster. This may take a moment ... ')
    dd_array = ss_calculator.get_degree_days_raster(prism_dict['tmin'], prism_dict['tmax'])

    print(f'- Saving raster to file.')
    dd_array.to_netcdf(local_raster_path)

    # Plotting to png
    print(f'- Plotting raster and saving to file.')
    dd_array.plot()
    plt.savefig(local_png_path)
    
    # upload to S3
    print('Uploading files to S3')
    response = s3_client.upload_file(local_raster_path, s3_bucket, s3_raster_loc)
    response = s3_client.upload_file(local_png_path, s3_bucket, s3_png_loc)

    return {
        'statusCode': 200,
        'body': json.dumps('Computation complete!')
    }