import boto3, decimal, json, time
import email_notify
import logging

TOLERABLEJITTER = 15000

dynamo = boto3.resource("dynamodb", region_name="us-east-1")
deviceTable = dynamo.Table("deviceping")

# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)


########################## lambda_handler


def check_user_devices(usermap):
    global deviceTable

    for itemUser in [usermap]:
        if "config" not in itemUser:
            continue

        getDeviceResponse = deviceTable.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("userid").eq(
                itemUser["userid"]
            ),
            ReturnConsumedCapacity="TOTAL",
        )
        deviceQueryItems = getDeviceResponse["Items"]
        logging.info(
            "Processing user: "
            + itemUser["email"]
            + " ("
            + str(len(deviceQueryItems))
            + " items, "
            + "notify "
            + str(itemUser["config"]["notificationEnabled"])
            + "/"
            + str(itemUser["config"]["notifyMissedPings"])
            + ")"
        )
        changedDevices = 0
        for device in deviceQueryItems:
            if CheckDevice(device=device, user=itemUser):
                changedDevices += 1
                update = {}
                update["UpdateExpression"] = "SET notify = :notify"
                update["ExpressionAttributeValues"] = {":notify": device["notify"]}
                logging.info(
                    json.dumps(
                        deviceTable.update_item(
                            Key={
                                "userid": itemUser["userid"],
                                "deviceid": device["deviceid"],
                            },
                            UpdateExpression=update["UpdateExpression"],
                            ExpressionAttributeValues=update[
                                "ExpressionAttributeValues"
                            ],
                        )
                    )
                )


########################## CheckDevice


def CheckDevice(device, user):
    logtext = "Processing deviceid: {} -- ".format(device["deviceid"])
    if "notify" not in device:
        device["notify"] = {}
    if "errorState" not in device["notify"]:
        device["notify"]["errorState"] = False
    if "lastNotified" not in device["notify"]:
        device["notify"]["lastNotified"] = 0
    notifyMissedPings = device["config"].get(
        "notifyMissedPings", user["config"]["notifyMissedPings"]
    )
    now = int(time.time() * 1000)
    mSecondsAgo = now - max(device["timer"]["lastPings"])
    if "knownInterval" in device["timer"]:
        if mSecondsAgo < (
            (device["timer"]["knownInterval"] * notifyMissedPings) + TOLERABLEJITTER
        ):
            if device["notify"]["errorState"] == True:
                device["notify"]["errorState"] = False
                logging.warn("{} Device flipped to errorState = False".format(logtext))
                return 1  # changed
            else:
                logging.info("{} Device still good".format(logtext))
                return 0  # device still good
        else:  # issue/bad
            if device["notify"]["errorState"] == True:
                logging.info("{} Device still bad".format(logtext))
                return 0  # device still bad
            else:
                logging.info("{} Device flipped to errorState = True".format(logtext))
                device["notify"]["errorState"] = True
                if user["config"]["notificationEnabled"] and not device["config"].get(
                    "disableNotification", False
                ):
                    lastNotifyTime = device["notify"]["lastNotified"]
                    msNotifyAgo = now - lastNotifyTime
                    if msNotifyAgo > 3600000:  # only notify if > 1 hour
                        logging.warn("NOTIFYING {}!".format(user.get("email","NONE")))
                        email_notify.SendEmail(
                            recipient=user.get("email", "dtype@dtype.org"),
                            device=device,
                        )
                        device["notify"]["lastNotified"] = now
                    else:
                        logging.warn("Not notifying. Still within re-notify limit.")
                else:
                    logging.warn("Not notifying. User or device has disabled notification.")
                return 1  # changed
    else:  # unknown or not yet consistent state
        logging.info("{} Device status unknown".format(logtext))
        return 0
