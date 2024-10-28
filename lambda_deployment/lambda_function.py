import json
from degree_day import degree_day as dd

def lambda_handler(event, context):
    
    lt = event['temp_low']
    ut = event['temp_high']
    print(f'The lower temperature threshold is: {lt}')
    print(f'The upper temperature threshold is: {ut}')

    dd_calc = dd.DegreeDayCalculator(lower_threshold=lt, upper_threshold=ut)

    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function run successful!')
    }

if __name__ == "__main__":

    event = {'temp_high': 30, 'temp_low': 8}
    print(lambda_handler(event=event, context='b'))