import pulumi
import pulumi_aws as aws

user_group_name = "existingUserGroup"
user_password = "YourSecurePassword123!"

# Create IAM Users
users = []
for i in range(25):
    user_name = f"clouduser{i:02d}"
    user = aws.iam.User(user_name, name=user_name)

    aws.iam.UserLoginProfile(f"{user_name}LoginProfile", 
                             user=user.name, 
                             password=user_password, 
                             password_reset_required=False)

    users.append(user.name)

# Add users to the existing group
aws.iam.UserGroupMembership("userGroupMembership", 
                            users=users, 
                            groups=[user_group_name])