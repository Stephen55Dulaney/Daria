# EC2 Security Group Settings for DARIA

You need to update your EC2 security group to allow traffic on the following ports:

- Port 5030: Memory Companion API
- Port 5035: Memory Companion Integration UI
- Port 8080: Test Server

## Instructions to Update Security Group

1. Go to the AWS Management Console
2. Navigate to EC2 → Security Groups
3. Find the security group associated with your EC2 instance
4. Click on "Edit inbound rules"
5. Add the following rules:
   - Type: Custom TCP, Port range: 5030, Source: Anywhere (0.0.0.0/0)
   - Type: Custom TCP, Port range: 5035, Source: Anywhere (0.0.0.0/0)
   - Type: Custom TCP, Port range: 8080, Source: Anywhere (0.0.0.0/0)
6. Click "Save rules"

## Alternative: Quick AWS CLI Command

If you have AWS CLI configured, you can run the following command (replace `sg-xxxxxxxx` with your security group ID):

```bash
aws ec2 authorize-security-group-ingress --group-id sg-xxxxxxxx --protocol tcp --port 5030 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id sg-xxxxxxxx --protocol tcp --port 5035 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id sg-xxxxxxxx --protocol tcp --port 8080 --cidr 0.0.0.0/0
```

## Update URLs

After updating the security group, you can access the following URLs:

- Test Page: http://3.12.144.184:8080/
- Memory Companion UI: http://3.12.144.184:5030/static/daria_memory_companion.html
- Memory Companion Integration: http://3.12.144.184:5035/ 