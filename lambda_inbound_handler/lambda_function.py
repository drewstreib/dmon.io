import boto3, json, time

TIMERPINGS = 4
TOLERABLEJITTER = 10000
MAXBODYTOPROCESS = 16000
MAXBODYTOWRITE = 4000
MININTERVAL = 40000

dynamo = boto3.resource("dynamodb")
deviceTable = dynamo.Table("deviceping")
userTable = dynamo.Table("deviceping-users")


def respond(err, res=None):
    return {
        "statusCode": "400" if err else "200",
        "body": err if err else json.dumps(res),
        "headers": {
            "Content-Type": "application/json",
        },
    }


def lambda_handler(event, context):
    try:
        userid = event["queryStringParameters"]["userid"]
        deviceid = event["queryStringParameters"]["deviceid"]
        key = {"userid": userid, "deviceid": deviceid}
    except:
        return respond("""{ "error": "Unable to parse userid and deviceid." }""")
    try:
        user = userTable.get_item(Key={"userid": userid})["Item"]
    except:
        return respond("""{ "error": "Invalid userid." } """)
    try:
        device = deviceTable.get_item(Key=key)["Item"]
    except:
        device = {}

    timems = round(time.time() * 1000)

    ####################### prep data
    lastPayload = event.get("body", None)
    if lastPayload:
        if len(lastPayload) > MAXBODYTOPROCESS:
            lastPayload = lastPayload[:MAXBODYTOPROCESS]
    lastEvent = {
        "requestContext": event.get("requestContext", None),
        "path": event.get("path", None),
    }
    doWriteConfig = False
    doWritePayload = True

    ####################### first time config & ignored/adopted
    if "config" not in device:
        config = {"adopted": False, "ignoreDevice": False}
        doWriteConfig = True
    else:
        config = device.get("config")
        if (not config["adopted"]) or (config["ignoreDevice"]):
            return respond("""{ "error": "Device ignored or not yet adopted." } """)

    ###################### timer
    timer = device.get("timer", {})
    if not "lastPings" in timer:
        timer["lastPings"] = []
    # check ping interval for MININTERVAL abuse
    if len(timer["lastPings"]) > 0:
        if timems - max(timer["lastPings"]) < MININTERVAL:  # too fast
            return respond(
                """{ "error": "Device check-in faster than allowed interval." } """
            )
    # update timer
    while len(timer["lastPings"]) >= TIMERPINGS:
        timer["lastPings"].remove(min(timer["lastPings"]))
    timer["lastPings"].append(timems)
    # see if we're consistent
    if len(timer["lastPings"]) == TIMERPINGS:
        ### !!SLOW next line
        diffs = [
            timer["lastPings"][i + 1] - timer["lastPings"][i]
            for i in range(len(timer["lastPings"]) - 1)
        ]
        if max(diffs) - min(diffs) <= TOLERABLEJITTER:
            timer["knownInterval"] = int(sum(diffs) / len(diffs))
            timer["isConsistent"] = True
        else:
            timer["isConsistent"] = False
    else:
        timer["isConsistent"] = False

    ####################### payload trim/compare with last
    if lastPayload:
        if len(lastPayload) > MAXBODYTOWRITE:
            lastPayload = lastPayload[:MAXBODYTOWRITE]
        if "lastPayload" in device:
            if device["lastPayload"] == lastPayload:
                doWritePayload = False

    ####################### write it
    if doWriteConfig:
        deviceTable.update_item(
            Key=key,
            UpdateExpression="SET config = :config",
            ExpressionAttributeValues={":config": config},
        )

    if doWritePayload:
        updateEx = "SET lastEvent = :last, lastPayload = :lp, timer = :timer ADD lifetimeCount :inc"
        updateVal = {":last": lastEvent, ":lp": lastPayload, ":timer": timer, ":inc": 1}
    else:
        updateEx = "SET lastEvent = :last, timer = :timer ADD lifetimeCount :inc"
        updateVal = {":last": lastEvent, ":timer": timer, ":inc": 1}
    return respond(
        None,
        json.dumps(
            deviceTable.update_item(
                Key=key, UpdateExpression=updateEx, ExpressionAttributeValues=updateVal
            )
        ),
    )
