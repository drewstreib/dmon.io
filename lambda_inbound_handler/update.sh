#!/bin/sh
zip dmon2_inbound.zip lambda_function.py
aws lambda update-function-code --function-name dmon2_inbound --zip-file fileb://dmon2_inbound.zip --publish
rm dmon2_inbound.zip
