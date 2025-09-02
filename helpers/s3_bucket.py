import pandas as pd
import boto3
import os

# AWS creds (better load from env vars)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")

AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")  # default region

S3_BUCKET = os.getenv("S3_BUCKET_NAME", "your-bucket-name")
 

# Initialize S3 client
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)

def read_csv_from_s3(bucket, key):
    """Read CSV directly into pandas from S3"""
    obj = s3.get_object(Bucket=bucket, Key=key)
    return pd.read_csv(obj["Body"])