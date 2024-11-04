# EntSoc 2024 Cloud Workshop
Author: Tim Farkas, EcoData Technology

## Getting Started

1. Log in to AWS console with [this login](https://tinyurl.com/entsoc2024-cloud-workshop)
    - AWS Account #: 440377999911
    - IAM username: guestuser1 (2,3, ...) 
    - Password: Ask Tim. 
2. Take 2 minutes to browse Services (top left of nav bar).

## Elastic Cloud Compute (EC2)
### Launch An EC2 Instance
1. Navigate to EC2 Dashboard, then `Instances` > `Instances` on the left nav bar.
2. Select `Launch instances`.
3. Name your instance with your initials: e.g., `entsoc-tef`.
4. Application and OS Images: 
    - Select `Ubuntu` card. 
    - Amazon Machine Image: `Ubuntu Server 24.04`.
    - Architecture: `64-bit (x84)`.
5. Instance Type: `t2.micro`.
6. Key Pair: `Proceed without a key pair`
7. Network Settings: Select "Existing security group" > Check `entsoc2024-guest-ec2` box.
8. Configure Storage: `8 GiB gp3`.
9. Advanced Settings
    - IAM Instance Profile: `entsoc2024-ec2-instance-profile-s3-only` 
10. Return to `Instances` > `Instances` and wait for your Instance State to be `Running`, about 30 seconds. You may need to refresh the browser.

### Explore and Connect To Your EC2 Instance
1. Click your `Instance ID` to view a summary of your instance configuration. 
2. Connect to your Instance: 
    - Click `Connect` > `EC2 Instance Connect` > `Connect using EC2 Instance Connect Endpoint`
    - Endpoint: `eice-078bd40ce8546647c`
    - Username: `ubuntu`
    - Click `Connect` to open a terminal window in your browser.
3. Submit command `ls -al` to see contents of your home directory.

### Download A File From S3
1. Install the AWS Command Line Interface (CLI):
``` bash 
sudo snap install aws-cli --classic
``` 
2. Check the CLI is installed: `aws --version`.
3. List the S3 buckets in your account: `aws s3 ls`.
4. List the contents of the workshop bucket: 
``` bash
aws s3 ls entsoc2024-ecodata-cloud-workshop 
```
5. Download the deployment package from the bucket: 
    - Get the deployment package URI from the S3 Console. 
    - Run `aws s3 cp <S3 URI> .` to download the package to your home directory. (Don't forget the `.` at the end of the command - it means "current directory".)
    - Check the download was successful with `ls -al`. 

## Serverless Compute with AWS Lambda Functions

### Create A Lambda Function
1. Navigate to the Lambda service. 
2. Select `Create function` > `Author from scratch`. 
3. Give it a name prefixed with `entsoc2024` and suffixed with your initials, e.g, `entsoc2024-tef`.
4. Runtime: `Python 3.9`.
5. Architecture: `x86_64`. 
6. Change default execution role: `Use an existing role` > `entsoc2024-lambda-role`.

### Hello World
7. In the `Code` tab, test the default function: 
    - Click `Test` > `Create new test event`. 
    - Click `Invoke`. 
    - Inspect the `Output` for results. 
8. Change line 4 ("TODO") to: `name = event['name']`
9. Change the argument to `json.dumps` to: `'Hello, ' + name + '!'`
10. Click `Deploy` to save your changes. Wait for function to update. 
11. Update the existing test event:
    - Change `key1` to `name`, and `value1` to `you gorgeous cloud user` (or whatever you want).
    - Click `Invoke`. 

### Deploy An Insect Phenology Model
12. Deploy the phenology model code: 
    - In another browser tab, navigate to the workshop S3 bucket. 
    - Select `lambda_deployment.zip` and copy the `URL` (not `S3 URI`) to your clipboard. 
    - In the Lambda Console, under the `Code` tab, select `Upload from` > `Amazon S3 location` and paste the URL. Hit `Save`.
    - Wait for the function to update, and take a minute to browse the new code.
13. Configure a new test: 
    - Replace the default test event with the following JSON, where `XX` is your 2-digit guest user number. E.g, `guestuser3` would use `20230103`.
``` python
{
    "date": "202301XX", 
    "lt": 0, 
    "ut": 30, 
    "user": "YOUR-INITIALS-OR-WHATEVER"
}
```
   - Click `Invoke` and inspect the `Output` for results.

### Update Function Config For Phenology Model
1. Increase system resources: 
    - `Configuration` > `General configuration` > `Edit`.
    - `Memory`: `512` MB. 
    - `Timeout`: `3` min `0` sec. 
    - `Save`. 
2. Switch to a custom network: 
    - `Configuration` > `VPC` > `Edit`. 
    - `VPC`: Name = `entsoc2024`. 
    - `Subnets`: Select all _private_ subnets, and NOT the public subnet. 
    - Security Group: `default` (`sg-067466a5f4c489420`).
    - `Save`
3. Mount a file system with Python dependencies pre-installed: 
    - `Configuration` > `File systems` > `Add file system`.
    - `EFS file system`: `entsoc2024-efs2`.
    - `Access point`: `entsoc-efs-mp2`.
    - `Local mount path`: `/mnt/python-dependencies`.
    - `Save`.
    




