import pulumi
import pulumi_aws as aws

# Variables
user_prefix = "clouduser"
user_count = 25
default_password = "YourDefaultPassword"
group_name = "your-existing-group-name"

# Create IAM users and set their login profiles
iam_users = []
for i in range(user_count):
    username = f"{user_prefix}{i:02d}"
    user = aws.iam.User(username, name=username)
    
    login_profile = aws.iam.UserLoginProfile(
        f"{username}-login-profile",
        user=user.name,
        password=default_password,
        password_reset_required=False
    )
    
    iam_users.append(user)

# Existing IAM group
iam_group = aws.iam.Group.get(group_name, id=group_name)

# Add users to the group
group_memberships = []
for user in iam_users:
    membership = aws.iam.UserGroupMembership(
        f"{user.name}-group-membership",
        user=user.name, 
        groups=[iam_group.id]
    )
    group_memberships.append(membership)

# Export the usernames of the created users
pulumi.export("created_usernames", [user.name for user in iam_users])