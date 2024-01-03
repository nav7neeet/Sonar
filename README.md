# Disaster Resilient Infrastructure

**Overview** <br>
A Python-based application designed to simplify the deployment, management, and cleanup of a robust and fault-tolerant infrastructure on Amazon Web Services (AWS). This application utilizes CloudFormation templates to create a disaster-resilient environment, ensuring continuous application availability even in the face of AWS availability zone or regional outages. The entire solution is designed and implemented with a focus on **production-grade standards**, ensuring stability, scalability, and security. The application supports two AWS regions: us-east-1 as the main region and us-east-2 as the backup region for disaster recovery.

**Main Infrastructure components:**
- VPC
- NAT Gateway
- Load Balancer
- Private EC2 Instances
- CloudFront Origin Group
- Secrets Manager
- S3 Cross-Region Replication
- Aurora Global Database

![image](https://github.com/nav7neeet/Sonar/assets/14819434/3cd4a0b1-661e-4683-b9c6-af62402629da)


## Features <br>
**Disaster Resilience and Fault Tolerance** <br>
The application creates an infrastructure that prioritizes disaster resilience and fault tolerance, allowing the application to remain operational in the event of an AWS availability zone or regional failure.


**Enhanced Security** <br>

- The application undergoes security scans using Checkov and Semgrep, ensuring that the infrastructure adheres to security best practices.
- Aurora database secrets are not hardcoded but stored securely in AWS Secrets Manager, adhering to security best practices.
- Instead of using traditional SSH keys, the application utilizes AWS Systems Manager Session Manager for a more secure means of connecting to EC2 instances.
##

**Deployment/Tear-Down** <br>

- A single Python script facilitates the deployment of the entire infrastructure across two AWS regions, streamlining the provisioning process.
- An additional script allows for easy and efficient resource cleanup.

**Easy Setup and Updates** <br>

- The Python script is designed to be simple, easy to understand, and maintainable, promoting efficient infrastructure management.
- The Python script is thoroughly documented with inline comments and a comprehensive guide, offering insights into each component and configuration option.
- It can be easily integrated with CI/CD systems, enabling automated create and update operations through the pipeline, enhancing deployment efficiency.
- The CloudFormation templates follow a consistent naming convention, aiding clarity and organization in the infrastructure.


## Usage
**Prerequisites:**

- AWS CLI configured with necessary permissions
- Install Python dependencies using pip install -r requirements.txt

<br>

- Run the python script setup-infra.py for deployment.
- Use python script destroy-infra.py for resource cleanup.
  
https://github.com/nav7neeet/Sonar/assets/14819434/5de28ad9-8491-461a-bd3b-c323970b88f9

##

**Conclusion** <br>
The Cloud Infrastructure Orchestrator is a powerful and versatile tool for deploying and managing a resilient and secure infrastructure on AWS. With comprehensive documentation and support for modern security practices, it offers a streamlined experience for both development and production environments.

## Requirements

- It should be easy to deploy and updates the infrastructure -- Just update the cloudformation template for the infrastrucute component and run the **infra-setup.py** script. Provide the same unique resource name.
- It should be possible to re-use the template to deploy a 2nd iteration of that infrastructure in the same AWS account and the same region -- Run the **setup-infra.py** script and provode unique resource prefix.

