# EntSoc 2024 Cloud Workshop
Author: Tim Farkas, EcoData Technology

## Getting Started

1. Log in to AWS console at: [text](https://tinyurl.com/entsoc2024-cloud-workshop)
    - AWS Account #: 440377999911
    - IAM username: guestuser1 (2,3, ...) 
    - Password: EntSoc2024!
2. Take 2 minutes to browse Services (top left of nav bar)

## Elastic Cloud Compute (EC2)

### Launch An EC2 Instance
1. Navigate to EC2 Dashboard, then `Instances` > `Instances` on the left nav bar
2. Select `Launch instances`
3. Name your instance with your initials: e.g., `entsoc-tef`
4. Application and OS Images: 
    - Select Ubuntu panel 
    - Amazon Machine Image: `Ubuntu Server 24.04`
    - Architecture: `64-bit (x84)`,
5. Instance Type: `t2.micro`
6. Key Pair: `Proceed without a key pair`
7. Network Settings: Select existing security group, check `entsoc2024-guest-ec2`
8. Configure Storage: `8 GiB gp3`.
9. Advanced Settings
    - IAM Instance Profile: `aws-ec2-s3-full-access-role` (Take note: "s3-full-access")
10. Return to `Instances` > `Instances` and wait for your Instance State to be `Running`.

### Explore and Connect To Your EC2 Instance

1. 