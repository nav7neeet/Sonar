import glob
import os
import re
import sys
import time
import boto3


# folder containing cloudformation templates
path = "templates"


def sortTemplates(templates):
    custom_order = []
    for template in templates:
        file_name = os.path.splitext(os.path.basename(template))[0]
        custom_order.append(file_name)

    # Define a custom sorting order
    sorting_order = {
        "nat-gateway": 0,
        "cloudfront": 1,
        "load-balancer": 2,
        "ec2-role": 3,
        "ec2": 4,
        "ec2-launch-template": 5,
        "s3-source": 6,
        "s3-destination": 7,
        "rds-secondary-cluster": 8,
        "rds-global-database": 9,
        "vpc": 10,
    }

    # Use the sorted function with a custom key based on the sorting order
    sorted_templates = sorted(
        custom_order, key=lambda x: sorting_order.get(x, float("inf"))
    )
    return sorted_templates


def delete_all_objects(bucket_name, region):
    """
    Delete all S3 objects, their versions, and delete markers in a given bucket.

    Parameters:
    - bucket_name (str): The name of the S3 bucket.

    Returns:
    - None
    """
    try:
        s3_client = boto3.client("s3", region_name=region)

        # List all objects in the bucket
        objects = s3_client.list_objects_v2(Bucket=bucket_name).get("Contents", [])

        # Delete all objects
        for obj in objects:
            s3_client.delete_object(Bucket=bucket_name, Key=obj["Key"])

        # List all object versions in the bucket
        versions = s3_client.list_object_versions(Bucket=bucket_name).get(
            "Versions", []
        )

        # Delete all object versions
        for version in versions:
            s3_client.delete_object(
                Bucket=bucket_name, Key=version["Key"], VersionId=version["VersionId"]
            )

        # List all delete markers in the bucket
        delete_markers = s3_client.list_object_versions(Bucket=bucket_name).get(
            "DeleteMarkers", []
        )

        # Delete all delete markers
        for delete_marker in delete_markers:
            s3_client.delete_object(
                Bucket=bucket_name,
                Key=delete_marker["Key"],
                VersionId=delete_marker["VersionId"],
            )
    except Exception as e:
        print(e)


def delete_aurora_cluster(global_cluster_identifier, cluster_identifier, region):
    # Create an RDS client
    rds = boto3.client("rds", region_name=region)

    try:
        # Describe the Aurora Global Database cluster
        response = rds.describe_db_clusters(DBClusterIdentifier=cluster_identifier)
        cluster_arn = response["DBClusters"][0]["DBClusterArn"]

        # first, remove cluster from the global cluster
        response = rds.remove_from_global_cluster(
            GlobalClusterIdentifier=global_cluster_identifier,
            DbClusterIdentifier=cluster_arn,
        )

        time.sleep(12)

        # Get the list of instances in the cluster
        instances = response["DBClusters"][0]["DBClusterMembers"]

        # Delete each db instance
        for instance in instances:
            response = rds.delete_db_instance(
                DBInstanceIdentifier=instance["DBInstanceIdentifier"],
                SkipFinalSnapshot=True,
            )

        # Delete the cluster
        rds.delete_db_cluster(
            DBClusterIdentifier=cluster_identifier,
            SkipFinalSnapshot=True,
        )

    except Exception as e:
        print(
            f"\nError listing or deleting instances in Aurora Global Database Cluster '{cluster_identifier}': {e}"
        )


if __name__ == "__main__":
    regions = ["us-east-1", "us-east-2"]

    # take user input for UNIQUE stack/resource prefix
    stack_prefix = input("enter unique stack/resource prefix: ")
    pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9]{0,20}$")
    if not pattern.match(stack_prefix):
        sys.exit(f"\nsupported characters: alphanumeric and < 20 chars")

    # get the list of cloudformation templates
    templates = glob.glob(f"./{path}/*.yaml") + glob.glob(f"./{path}/*.yml")

    # sort the templates to start deleting the stack which was created last
    sorted_templates = sortTemplates(templates)

    for region in regions:
        print(f"\n============ deleting resources in {region} ============")
        # create boto3 client
        client = boto3.client("cloudformation", region_name=region)

        for template in sorted_templates:
            if template == "s3-source":
                bucket = f"{stack_prefix}-bucket-us-east-1"
                print(f"\ndelete objects in bucket: {bucket}")
                delete_all_objects(bucket, "us-east-1")

            if template == "s3-destination":
                bucket = f"{stack_prefix}-bucket-us-east-2"
                print(f"\ndelete objects in bucket: {bucket}")
                delete_all_objects(bucket, "us-east-2")

            if template == "rds-secondary-cluster":
                delete_aurora_cluster(
                    f"{stack_prefix}-global-cluster",
                    f"{stack_prefix}-secondary-cluster",
                    "us-east-2",
                )

                delete_aurora_cluster(
                    f"{stack_prefix}-global-cluster",
                    f"{stack_prefix}-primary-cluster",
                    "us-east-1",
                )

            stack_name = f"{stack_prefix}--{template}"
            print(f"\ndeleting stack {stack_name}")
            try:
                response = client.delete_stack(StackName=stack_name)
                waiter = client.get_waiter("stack_delete_complete")
                var = waiter.wait(
                    StackName=stack_name,
                    WaiterConfig={"Delay": 10, "MaxAttempts": 135},
                )
                if var is None:
                    print(f"{stack_name} stack deleted successfully")
            except Exception as e:
                sys.exit(f"\nError deleting stack {stack_name}: {e}")
