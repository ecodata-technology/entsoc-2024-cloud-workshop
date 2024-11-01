import json
import shutil
import urllib
import os
import zipfile
import boto3
from degree_day import degree_day as dd
import xarray as xra
import matplotlib.pyplot as plt


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

    ## Variables 
    print("Loading Common Variables and Objects")
    # storage_dir = "/home/ec2-user/prism-etl" # do not change me
    storage_dir = "/tmp/prism-etl" # for lambda 
    weather_var_list = ['tmin', 'tmax'] 
    base_url = 'https://services.nacse.org/prism/data/public/4km'
    format = 'nc'
    s3_bucket = 'entsoc2024-ecodata-cloud-workshop'
    s3_client = boto3.client('s3')
    gdd_dir = os.path.join(storage_dir, 'gdd')
    if os.path.exists(gdd_dir):
        shutil.rmtree(gdd_dir)
    os.makedirs(gdd_dir)

    ## Common Objects
    target_date = event['date']
    lt = event['temp_low']
    ut = event['temp_high']
    user = event['user']
    raster_name = f'gdd_raster_user={user}_date={target_date}_lt={lt}_ut={ut}.nc'
    local_raster_path = os.path.join(gdd_dir, raster_name)
    png_name = f'gdd_raster_user={user}_date={target_date}_lt={lt}_ut={ut}.png'
    local_png_path = os.path.join(gdd_dir, png_name)
    s3_raster_loc = f'gdd_rasters/{user}/{raster_name}'
    s3_png_loc = f'gdd_rasters/{user}/{png_name}'
        

    for var in weather_var_list:
        print(f"Pulling {var} data")
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
        
    # create GDD artifacts
    print('Creating GDD artifacts.')
    prism_dict = {} 

    for var in weather_var_list:

        print(f'- Loading {var} NetCDF file.')
        file_name = f'PRISM_{var}_stable_4kmD2_{target_date}_nc.nc'
        file_path = os.path.join(storage_dir, var, target_date, file_name)
        prism_dict[var] = xra.open_dataset(file_path, engine = 'netcdf4').Band1

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

if __name__ == "__main__":

    event = {'temp_high': 30, 'temp_low': 8, 'date': '20211022', 'user': 'tfarkas'}
    print(lambda_handler(event=event, context='b'))