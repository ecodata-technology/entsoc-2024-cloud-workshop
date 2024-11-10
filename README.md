# EntSoc 2024 Cloud Workshop
Author: Tim Farkas, EcoData Technology

## Getting Started
1. Log in to AWS console with [this login](https://440377999911.signin.aws.amazon.com/console)
    - AWS Account #: 440377999911
    - IAM username: cloudUser0 (2,3, ..., 149) 
    - Password: Ask Tim. 
2. Take 1 minute to browse Services (top left of nav bar).

## Simple Storage Service (S3)
1. Navigate to S3 console. 
2. Navigate to `entsoc2024-ecodata-cloud-workshop/uploads`.
3. Download a file from S3 to your local machine. 
    - Select the checkbox for your desired file. 
    - Click `Download`. 
4. Create a new folder: 
   - `Create folder`. 
   - Enter a unique folder name, such as your username. 
   - Don't specifiy an encryption key. 
   - `Create folder`. 
5. Upload a small file from your local machine.
    - Note: Other workshop participants will have access to your uploaded files. 
    - `Upload` > `Add files` > Select file > `Upload` 
    - Wait for the upload to finish, then close the upload details page. 

## Elastic Cloud Compute (EC2)
### Launch An EC2 Instance 
1. Navigate to EC2 Dashboard, then `Instances` > `Instances` on the left nav bar.
2. Make sure you are in region `N. Virginia` (top nav bar).
3. Select `Launch instances`.
4. Name your instance with your username: e.g., `cloudUser149`.
5. Application and OS Images: 
    - Select `Ubuntu` card. 
    - Amazon Machine Image: `Ubuntu Server 24.04`. (default)
    - Architecture: `64-bit (x84)`. (default)
6. Instance Type: `t2.micro`. (default)
7. Key Pair: `Proceed without a key pair`.
8. Network Settings: Select "Existing security group" > Check `entsoc2024-guest-ec2` box.
9. Configure Storage: `8 GiB gp3`. (default)
10. Advanced Details:
    - IAM Instance Profile: `entsoc2024-ec2-instance-profile-s3-only` 
11. Select `Launch Instance`. 
11. Return to `Instances` > `Instances` and wait for your Instance State to be `Running`, about 30 seconds. You may need to refresh the browser.

### Explore and Connect To Your EC2 Instance
1. Click your `Instance ID` to view a summary of your instance configuration. 
2. Connect to your Instance: 
    - Click `Connect` > `EC2 Instance Connect` > `Connect using EC2 Instance Connect Endpoint`
    - Endpoint: `eice-078bd40ce8546647c` (default)
    - Username: `ubuntu` (default)
    - Click `Connect` to open a terminal window in your browser.
3. View the contents of your home directory: `ls -al`.
4. Create a new file: `touch deleteme.txt`.
5. View the contents of your home directory `ls -al`.
6. Delete the file: `rm deleteme.txt`.

### Use the AWS CLI
1. Install the AWS Command Line Interface (CLI): `sudo snap install aws-cli --classic`
2. Check the CLI is installed: `aws --version`.
3. List the S3 buckets in your account: `aws s3 ls`.
4. List the contents of the workshop bucket: `aws s3 ls entsoc2024-ecodata-cloud-workshop`
5. Download a file from S3: 
    - Get the S3 URI of your desired file from the S3 Console. 
    - Run `aws s3 cp <S3 URI> .` to download the package to your home directory. (Don't forget the `.` at the end of the command - it means "current directory".)
    - Check the download was successful with `ls -al`. 
6. Stop your instance in the Console: Select instance > `Instance state` > `Stop instance` > `Stop`. 

## Serverless Compute with AWS Lambda Functions
### Create A Lambda Function
1. Navigate to the Lambda service. 
2. Select `Create function` > `Author from scratch`. 
3. Give it a name prefixed with `entsoc2024` and suffixed with your initials, e.g, `entsoc2024-tef`.
4. Runtime: `Python 3.9`.
5. Architecture: `x86_64`. 
6. Change default execution role: `Use an existing role` > `entsoc2024-lambda-role`.
7. Click `Create function`.

### Hello World
1. In the `Code` tab, test the default function: 
    - Click `Test` > `Create new test event`. 
    - Click `Invoke` and inspect the `Output` for results. 
2. Change line 4 ("#TODO") to: `name = event['name']`. Preserve the indendataion!
3. Change the argument to `json.dumps` to: `'Hello, ' + name + '!'`
4.  Click `Deploy` to save your changes. Wait for function to update. 
5.  Update the existing test event:
    - Change `key1` to `name`, and `value1` to `you gorgeous cloud user` (or whatever you want).
    - Click `Invoke` and inspect the `Output` for results. 

### Update Function Config For A Phenology Model 
1. Increase system resources: 
    - `Configuration` > `General configuration` > `Edit`.
    - Memory: `1024` MB. 
    - Timeout: `3` min `0` sec. 
    - `Save`. 
2. Switch to a custom network: 
    - `Configuration` > `VPC` > `Edit`. 
    - VPC: Name = `entsoc2024`. 
    - Subnets: Select all _private_ subnets and NOT the public subnet. 
    - Security Group: `default` (`sg-067466a5f4c489420`).
    - `Save`
3. Mount a file system with Python dependencies pre-installed: 
    - `Configuration` > `File systems` > `Add file system`.
    - EFS file system: `entsoc2024-efs2`.
    - Access point: `entsoc-efs-mp2`.
    - Local mount path: `/mnt/ecodata2024-efs`.
    - `Save`.

### Deploy An Insect Phenology Model
1. Deploy the phenology model code: 
    - In another browser tab, navigate to the workshop S3 bucket. 
    - Select `lambda_deployment.zip` and copy the `URL` (not `S3 URI`) to your clipboard. 
    - In the Lambda Console, under the `Code` tab, select `Upload from` > `Amazon S3 location` and paste the URL. Hit `Save`.
    - Wait for the function to update, and take a minute to browse the new code.
2. Configure a new test: 
    - Replace the default test event with JSON below, but where `AA` in the date entry is your 2-digit table number, and `BB` is the last digit of your user number + 1. E.g, `cloudUser3` would use `20000401`. `cloudUser29` would use `20021001`. (Sorry, this is a little complicated). 

``` python
{
    "date": "20AABB01", 
    "state": "Arizona",
    "temp_low": 0, 
    "temp_high": 30, 
    "user": "YOUR-INITIALS-OR-WHATEVER"
}
```
   - Click `Invoke` and inspect the `Output` for results.
   - Note: PRISM allows only two downloads from the same IP per day. If you get an error about the download, try another date in your year and month. 
3. View the results. 
    - Navigate to S3 > `entsoc2024-ecodata-cloud-workshop/gdd-rasters/YOUR-USER-VALUE-FROM-TEST-EVENT`.
    - Download and view the `.png` file on your local machine.

### Run A Different Model

If you like, go ahead and run a phenology model for an actual insect. Below are example, emprically derived temperature thresholds for a handful of economically important pest, care of Seth Dorman (ARS / Oregon State University). The models should be most accurate for the state of Oregon, but you can change the state to anything you like. 

Again, remember that PRISM only allows two downloads per day from the same IP.

| Pest Species | Lower Threshold | Upper Threshold |
|----------|----------|----------|
| True armyworm | 10 | 29 |
| Red clover casebearer | 12.3 | 100 |
| Cereal leaf beetle | 8.9 | 37.8 |
| Black cutworm | 9.8 | 36 |
| Codling moth | 10 | 31.1 |
| Filbertworm| 10 | 33.3 |
| Cabbage looper | 10| 32.2 |
| Brown marmorated stink bug| 12.2 | 33.3 |
| Corn earworm | 12.8 | 33.3 |
| Spotted wing Drosophila| 10 | 31.1 |

### Trigger Your Function With An HTTP Request
1. Configure a URL trigger: 
    - `Configuration` > `Function URL` > `Create function URL`. 
    - `Auth type`: None.
    - `Save`.
2. Copy and paste your function URL to a browser tab. 
3. Input the event parameters as a query string: e.g., `?date=20230101&state=New%20Mexico&temp_low=10&temp_high=29&user=gorgeousclouduser`.
4. Submit the request and wait for the results in the browser page. 
5. Look in S3 for your results. 



