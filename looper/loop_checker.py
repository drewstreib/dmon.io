import boto3, decimal, json
import logging
#import schedule, time
import time
import check_user_devices

logging.basicConfig(level=logging.INFO)

def check_all():
    start = time.time()
    dynamo = boto3.resource("dynamodb", region_name="us-east-1")
    userTable = dynamo.Table("deviceping-users")

    pe = "userid, email, config, entitlement"

    response = userTable.scan(ProjectionExpression=pe)
    for i in response["Items"]:
        check_user_devices.check_user_devices(i)

    while "LastEvaluatedKey" in response:
        response = userTable.scan(
            ProjectionExpression=pe, ExclusiveStartKey=(response["LastEvaluatedKey"])
        )
        for i in response["Items"]:
            check_user_devices.check_user_devices(i)
    logging.info("check_all() loop ran in: {}".format(time.time() - start))


def main():
    logging.info("Starting main()")
    #schedule.every(60).seconds.do(check_all)
    while True:
        #schedule.run_pending()
        check_all()
        time.sleep(55)


if __name__ == "__main__":
    main()
