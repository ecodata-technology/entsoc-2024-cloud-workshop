import json
from degree_day import DegreeDayCalculator
# import xarray as xra

def lambda_handler(event, context):
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

if __name__ == "__main__":

    print(lambda_handler(event='a', context='b'))