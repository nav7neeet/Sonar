import os
import glob
import re
import sys
import boto3
from ruamel.yaml import YAML

# folder containing cloudformation templates
path = "templates"


def updateYaml(yamlFile, newValue):
    """
    Update specific values in a YAML file.

    Parameters:
    - yamlFile (str): Path to the YAML file to be updated.
    - newValue (dict): A dictionary containing key-value pairs to update in the YAML file.

    Returns:
    - None

    Note:
    - The function reads the YAML file, locates the specified keys in the "Parameters" section,
      and updates their "Default" values with the corresponding values from the newValue dictionary.
    """

    yaml = YAML()

    with open(yamlFile, "r") as file:
        data = yaml.load(file)
        for key, value in newValue.items():
            if "Parameters" in data and key in data["Parameters"]:
                data["Parameters"][key]["Default"] = value

    with open(yamlFile, "w") as file:
        yaml.dump(data, file)


def sortTemplates(templates):
    """
    Sort a list of template file paths based on a custom order.

    Parameters:
    - templates (list of str): A list of file paths for templates to be sorted.

    Returns:
    - list of str: The sorted list of template file paths.
    """

    custom_order = []
    for template in templates:
        file_name = os.path.splitext(os.path.basename(template))[0]
        custom_order.append(file_name)

    # Define a custom sorting order
    sorting_order = {
        "vpc": 0,
        "ec2-role": 1,
        "ec2-launch-template": 2,
        "nat-gateway": 3,
        "ec2": 4,
        "load-balancer": 5,
        "cloudfront": 6,
        "s3-source": 7,
        "s3-destination": 8,
        "rds-global-database": 9,
        "rds-secondary-cluster": 10,
    }

    # Use the sorted function with a custom key based on the sorting order
    sorted_templates = sorted(
        custom_order, key=lambda x: sorting_order.get(x, float("inf"))
    )
    return sorted_templates


def validate_template(templates):
    """
    Validate CloudFormation templates against the AWS CloudFormation service.

    Parameters:
    - templates (list of str): A list of file paths for CloudFormation templates to be validated.

    Returns:
    - bool: True if all templates are valid, otherwise exits the program with an error message.
    """
    client = boto3.client("cloudformation")
    for template in templates:
        try:
            with open(template, "r") as file:
                file_contents = file.read()
            response = client.validate_template(TemplateBody=file_contents)
        except Exception as e:
            sys.exit(f"Invalid template: {template}: {e}")
    return True


def stack_exists(client, file_name, stack_prefix):
    """
    Check if a CloudFormation stack with a specific name exists.

    Parameters:
    - client (boto3.client): The AWS CloudFormation client.
    - file_name (str): The name or unique identifier of the CloudFormation stack.
    - stack_prefix (str): The prefix to be used when constructing the full stack name.

    Returns:
    - str or None: The status of the stack if it exists, otherwise None.
    """
    response = client.list_stacks()
    stack_name = f"{stack_prefix}--{file_name}"

    for stack in response["StackSummaries"]:
        if stack.get("StackName") == stack_name:
            return stack.get("StackStatus")


def cloudformation_stack(client, file_name, stack_prefix, mode):
    """
    Create or update an AWS CloudFormation stack.

    Parameters:
    - client (boto3.client): The AWS CloudFormation client.
    - file_name (str): The name or unique identifier of the CloudFormation stack.
    - stack_prefix (str): The prefix to be used when constructing the full stack name.
    - mode (str): The operation mode, either "create" or "update".

    Returns:
    - bool: True if the operation is successful, otherwise exits the program with an error message.

    Note:
    - The function reads the content of the specified YAML file for the CloudFormation stack.
    - It then creates or updates the stack based on the specified mode ("create" or "update").
    - The function uses waiters to wait for the stack creation or update to complete.
    - If the operation is successful, it returns True; otherwise, it exits the program with an error message.
    """
    stack_name = f"{stack_prefix}--{file_name}"
    try:
        with open(f"./{path}/{file_name}.yml", "r") as file:
            file_contents = file.read()

        if mode == "create":
            waiter = client.get_waiter("stack_create_complete")
            response = client.create_stack(
                StackName=stack_name,
                TemplateBody=file_contents,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {
                        "ParameterKey": "StackPrefix",
                        "ParameterValue": stack_prefix,
                    }
                ],
            )
        elif mode == "update":
            waiter = client.get_waiter("stack_update_complete")
            response = client.update_stack(
                StackName=stack_name,
                TemplateBody=file_contents,
                Capabilities=["CAPABILITY_NAMED_IAM"],
                Parameters=[
                    {
                        "ParameterKey": "StackPrefix",
                        "ParameterValue": stack_prefix,
                    }
                ],
            )

        var = waiter.wait(
            StackName=stack_name,
            WaiterConfig={"Delay": 10, "MaxAttempts": 135},
        )
        if var is None:
            return True
    except Exception as e:
        if "No updates are to be performed" in str(e):
            print("no updates to perform..")
            return False
        else:
            sys.exit(f"Error {mode} stack {file_name}: {e}")


if __name__ == "__main__":
    regions = ["us-east-1", "us-east-2"]

    # take user input for UNIQUE stack/resource prefix
    stack_prefix = input("enter unique stack/resource prefix: ")
    pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9]{0,20}$")
    if not pattern.match(stack_prefix):
        sys.exit(f"\nsupported characters: alphanumeric and < 20 chars")

    # get the list of cloudformation templates
    templates = glob.glob(f"./{path}/*.yaml") + glob.glob(f"./{path}/*.yml")

    # validate the cloudformation templates
    print(f"\nvalidating cloudformation templates...")
    if validate_template(templates):
        print(f"\ntemplate validation successful")

    # sort the templates before stack creation as stacks must be created in specific order
    sorted_templates = sortTemplates(templates)

    for region in regions:
        print(f"\n============ creating/updating resources in {region} ============")

        for template in sorted_templates:
            # create boto3 cloudformation client
            client = boto3.client("cloudformation", region_name=region)
            flag = False

            if region == "us-east-1" or region == "us-east-2":
                if template in [
                    "vpc",
                    "ec2-launch-template",
                    "nat-gateway",
                    "ec2",
                    "load-balancer",
                ]:
                    flag = True

            if region == "us-east-1" and template in [
                "ec2-role",
                "cloudfront",
                "rds-global-database",
            ]:
                flag = True

            if region == "us-east-1" and template == "s3-source":
                client = boto3.client("cloudformation", region_name="us-east-2")
                template = "s3-destination"
                flag = True

            if region == "us-east-2" and template == "cloudfront":
                # update cloudfront template with the lb dns name
                response = client.describe_stacks(
                    StackName=f"{stack_prefix}--load-balancer"
                )
                outputs = response["Stacks"][0]["Outputs"]
                for output in outputs:
                    if output.get("ExportName") == f"{stack_prefix}-ALBDNSName":
                        value = output.get("OutputValue")
                        break
                updateYaml(f"./{path}/cloudfront.yml", {"ALBDNSOhio": value})

                client = boto3.client("cloudformation", region_name="us-east-1")
                status = stack_exists(client, template, stack_prefix)
                if status != "DELETE_COMPLETE":
                    print(f"\n{template} stack exists & status= {status}")
                    cloudformation_stack(client, template, stack_prefix, mode="update")

            if region == "us-east-2" and template == "rds-secondary-cluster":
                flag = True

            if region == "us-east-2" and template == "s3-destination":
                client = boto3.client("cloudformation", region_name="us-east-1")
                template = "s3-source"
                flag = True

            if flag:
                status = stack_exists(client, template, stack_prefix)
                if status is not None and status != "DELETE_COMPLETE":
                    print(
                        f"\n{stack_prefix}--{template} stack exists & status= {status}"
                    )
                    update = cloudformation_stack(
                        client, template, stack_prefix, mode="update"
                    )
                    if update:
                        print(f"{stack_prefix}--{template}: stack updated")
                else:
                    print(f"\n{stack_prefix}--{template}: stack does not exist")
                    cloudformation_stack(client, template, stack_prefix, mode="create")
                    print(f"{stack_prefix}--{template}: stack created")
