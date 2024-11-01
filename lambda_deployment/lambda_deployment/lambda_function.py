import json
import boto3
from degree_day import degree_day as dd
import urllib
import os
import zipfile

def lambda_handler(event, context):
   
    # Test connection to internet 
    print('Testing internet connection...')
    try:
        response = urllib.request.urlopen('https://aws.amazon.com')
        status_code = response.getcode()
        print(f'Response Code: {status_code}. Internet connection established!')
    except Exception as e:
        print('Error:', e)
        raise e

    ## Variables 
    print("Loading Common Variables and Objects")
    storage_dir = "/tmp/" # do not change me
    # time_lag_days = 2
    # bbox_file_name = 'or-bbox.geojson'
    # bbox_file_location = '/'
    weather_var_list = ['tmin', 'tmax'] 
    base_url = 'https://services.nacse.org/prism/data/public/4km'
    format = 'nc'
    # s3_bucket = 'usda-ars-dormanlab-cdd-app'
    s3_client = boto3.client('s3')
    gdd_dir = os.path.join(storage_dir, 'gdd')

    ## Common Objects
    target_date = event['date']
    # bbox_file_path = os.path.join(bbox_file_location, bbox_file_name)
    # bbox = gpd.read_file(bbox_file_path)
    # with open('pest_params.yaml') as f:
    #     pest_params = yaml.full_load(f)
    # pests = list(pest_params.keys())
    lt = event['temp_low']
    ut = event['temp_high']
    print(f'The lower temperature threshold is: {lt}')
    print(f'The upper temperature threshold is: {ut}')

    dd_calc = dd.DegreeDayCalculator(lower_threshold=lt, upper_threshold=ut)

    for var in weather_var_list:
        print(f"- Pulling {var} data")
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
            weather_pull_succeeded = False
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
        with zipfile.ZipFile(dest_file, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        
        print(f'- Successfully pulled {var}')
        
        prism_dict = {} 
        # for var in ['tmin', 'tmax']:
        #     print(f'- Clipping {var} raster to bounding box.')
        #     # load var
        #     dest_dir = os.path.join(storage_dir, var, target_date)
        #     raw_raster = rioxarray.open_rasterio(os.path.join(dest_dir, f'prism_{var}_us_30s_{target_date}.bil'))
        #     or_raster = raw_raster.rio.clip(bbox.geometry, drop = True)
        #     or_raster = or_raster.where(or_raster != -9999)
        #     prism_dict[var] = or_raster.drop_vars('band').squeeze()
        #     del raw_raster, or_raster
    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function run successful!')
    }

if __name__ == "__main__":

    event = {'temp_high': 30, 'temp_low': 8, 'date': '20211010'}
    print(lambda_handler(event=event, context='b'))