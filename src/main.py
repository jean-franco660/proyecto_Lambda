import boto3
import csv
import json
import io
import re
import os
import logging
from datetime import datetime

# --- Setup Logging ---
# Use Python's logging module for better log management in CloudWatch
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Initialize AWS Clients ---
s3 = boto3.client('s3')

# --- Environment Variables ---
# Best practice: Get configuration from environment variables set by Terraform/AWS
# This avoids hardcoding values and makes the function reusable.
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET_NAME')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE') # Variable is set, so let's get it

# --- Constants ---
DATE_FORMATS = [
    "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
    "%m/%d/%Y %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y %I:%M %p"
]

TERRITORY_MAP = {
    "USA": "NA", "France": "EMEA", "Australia": "APAC",
    "Japan": "APAC", "Germany": "EMEA", "UK": "EMEA", "Spain": "EMEA"
}

# --- Helper Functions ---

def parse_date(date_str):
    """Attempts to parse a date string with multiple formats."""
    if not isinstance(date_str, str):
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime('%Y-%m-%d')
        except (ValueError, TypeError):
            continue
    return None

def is_numeric(value):
    """Checks if a value can be converted to a float."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False

def sanitize_text(value):
    """Removes non-alphanumeric characters (except whitespace) and strips."""
    if not value or not isinstance(value, str):
        return ""
    return re.sub(r'[^\w\s]', '', value).strip()

def sanitize_phone(phone):
    """Cleans a phone number, returning only digits."""
    if not phone or not isinstance(phone, str):
        return None
    cleaned = re.sub(r'\D', '', phone)
    return cleaned if len(cleaned) >= 7 else None

# --- Main Lambda Handler ---

def handler(event, context):
    """
    This function is triggered by an S3 event. It reads a CSV file, cleans and
    validates its data, and saves the result as a JSON file in another S3 bucket.
    """
    # Ensure environment variables are set
    if not OUTPUT_BUCKET:
        logger.error("FATAL: Environment variable OUTPUT_BUCKET_NAME is not set.")
        return {'statusCode': 500, 'body': 'Server configuration error.'}

    # Initialize variables to prevent UnboundLocalError in exception blocks
    bucket_name, object_key = None, None
    try:
        # 1. Get object details from the event
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        object_key = event['Records'][0]['s3']['object']['key']
        logger.info(f"Processing file: s3://{bucket_name}/{object_key}")

        # 2. Read the object from S3
        response = s3.get_object(Bucket=bucket_name, Key=object_key)
        body = response['Body'].read()

        # Decode with fallback for different encodings
        try:
            csv_content = body.decode('utf-8')
        except UnicodeDecodeError:
            csv_content = body.decode('latin-1')

        reader = csv.DictReader(io.StringIO(csv_content))
        
        clean_rows = []
        seen_rows = set()
        processed_count = 0
        skipped_count = 0

        # 3. Process each row in the CSV
        for row in reader:
            processed_count += 1
            
            # --- Data Validation and Cleaning ---
            qty_str = row.get('QUANTITYORDERED', '').strip()
            if not qty_str.isdigit() or int(qty_str) <= 0:
                skipped_count += 1
                continue
            row['QUANTITYORDERED'] = int(qty_str)

            price_str = row.get('PRICEEACH', '').strip()
            if not is_numeric(price_str) or float(price_str) < 0:
                skipped_count += 1
                continue
            row['PRICEEACH'] = float(price_str)

            order_date = parse_date(row.get('ORDERDATE'))
            if not order_date:
                skipped_count += 1
                continue
            row['ORDERDATE'] = order_date

            # Validate required identifiers
            if not row.get('ORDERNUMBER', '').isdigit() or not row.get('ORDERLINENUMBER', '').isdigit():
                skipped_count += 1
                continue

            # --- Data Transformation and Enrichment ---
            status = row.get('STATUS', '').strip().upper()
            row['STATUS'] = "DELIVERED" if status == "DLEIVERED" else (status or "UNKNOWN")

            sales_str = row.get('SALES', '').strip()
            sales = float(sales_str) if is_numeric(sales_str) else 0.0
            calc_sales = row['QUANTITYORDERED'] * row['PRICEEACH']
            row['SALES'] = round(calc_sales, 2) if abs(sales - calc_sales) > 0.1 else sales

            msrp_str = row.get('MSRP', '').strip()
            if is_numeric(msrp_str):
                msrp = float(msrp_str)
                row['MSRP'] = msrp
                row['MSRP_ISSUE'] = row['PRICEEACH'] > msrp
            else:
                row['MSRP'] = None
                row['MSRP_ISSUE'] = False

            country = sanitize_text(row.get('COUNTRY', ''))
            row['COUNTRY'] = country
            row['TERRITORY'] = row.get('TERRITORY') or TERRITORY_MAP.get(country, 'UNKNOWN')

            row['CITY'] = row.get('CITY', '').strip() or "SIN CIUDAD"
            
            # --- Sanitize remaining fields ---
            row['PRODUCTCODE'] = row.get('PRODUCTCODE', '')[:15]
            row['PRODUCTLINE'] = row.get('PRODUCTLINE', '')[:60]
            row['PHONE'] = sanitize_phone(row.get('PHONE'))
            row['CONTACTLASTNAME'] = sanitize_text(row.get('CONTACTLASTNAME', ''))
            row['CONTACTFIRSTNAME'] = sanitize_text(row.get('CONTACTFIRSTNAME', ''))
            row['DEALSIZE'] = sanitize_text(row.get('DEALSIZE', ''))

            # --- Deduplication ---
            row_tuple = tuple(sorted(row.items()))
            if row_tuple in seen_rows:
                skipped_count += 1
                continue
            seen_rows.add(row_tuple)

            clean_rows.append(row)

        logger.info(f"Total rows processed: {processed_count}. Rows cleaned: {len(clean_rows)}. Rows skipped: {skipped_count}.")

        # 4. Write the cleaned data to the output bucket
        if clean_rows:
            output_key_name = os.path.splitext(object_key)[0] + '.json'
            s3.put_object(
                Bucket=OUTPUT_BUCKET,
                Key=output_key_name,
                Body=json.dumps(clean_rows, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )
            logger.info(f"Successfully wrote cleaned file to: s3://{OUTPUT_BUCKET}/{output_key_name}")
            return {
                'statusCode': 200,
                'body': f'Successfully processed {object_key}. Cleaned data at {output_key_name}.'
            }
        else:
            logger.warning("No valid rows found after cleaning. No output file was generated.")
            return {
                'statusCode': 200,
                'body': 'Processed file, but no valid data found to save.'
            }

    except s3.exceptions.NoSuchKey:
        error_msg = f"Error: The object key '{object_key}' does not exist in bucket '{bucket_name}'."
        logger.error(error_msg)
        return {'statusCode': 404, 'body': 'File not found.'}
    except (KeyError, IndexError) as e:
        logger.exception(f"Error parsing S3 event structure: {e}")
        return {'statusCode': 400, 'body': 'Malformed S3 event trigger.'}
    except Exception as e:
        # Log the full exception traceback for easier debugging in CloudWatch
        logger.exception("An unexpected error occurred during execution.")
        return {
            'statusCode': 500,
            'body': f'Error processing file: {str(e)}'
        }
