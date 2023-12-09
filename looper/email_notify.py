import boto3, decimal, json
from botocore.exceptions import ClientError
import logging

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


def SendEmail(recipient, device):
    SENDER = "dMon.io Notifier <notifications@dMon.io>"
    # CONFIGURATION_SET = "ConfigSet"
    AWS_REGION = "us-east-1"
    SUBJECT = "dMon.io - Device Failure! (" + device["deviceid"] + ")"

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = json.dumps(device, cls=DecimalEncoder, indent=4, separators=(",", ": "))
    BODY_HTML = (
        """<html><head></head><body><h1>dMon.io - Device Failure!</h1></body></html>"""
    )
    CHARSET = "UTF-8"

    client = boto3.client("ses", region_name=AWS_REGION)

    # Try to send the email.
    try:
        response = client.send_email(
            Destination={
                "ToAddresses": [
                    recipient,
                ],
            },
            Message={
                "Body": {
                    #'Html': {
                    #    'Charset': CHARSET,
                    #    'Data': BODY_HTML,
                    # },
                    "Text": {
                        "Charset": CHARSET,
                        "Data": BODY_TEXT,
                    },
                },
                "Subject": {
                    "Charset": CHARSET,
                    "Data": SUBJECT,
                },
            },
            Source=SENDER,
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.warn("Email sent! Message ID:")
        logging.warn(response["ResponseMetadata"]["RequestId"])
