import json
from degree_day import DegreeDayCalculator

def lambda_handler(event, context):
    
    print(f'The lower temperature threshold is: {event["temp_low"]}')
    print(f'The upper temperature threshold is: {event["temp_high"]}')

    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function run successful!')
    }

if __name__ == "__main__":

    event = {'temp_high': 30, 'temp_low': 8}
    print(lambda_handler(event=event, context='b'))