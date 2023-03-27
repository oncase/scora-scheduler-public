import boto3
import json

REGIONS = ["us-east-1", "us-east-2"] #regions where resources will be searched for
ACCEPTED_ACTIONS = ["START", "STOP"]


def get_tag_from_type(type):
    return f"SCORA_SCHEDULER_AUTO_{type}"


# this function uses
def get_resource_tags(resource_arn, region):
    tag_client = boto3.client("resourcegroupstaggingapi", region_name=region)
    tag_response = tag_client.get_resources(ResourceARNList=[resource_arn])

    if not len(tag_response["ResourceTagMappingList"]):
        return []
    return tag_response["ResourceTagMappingList"][0]["Tags"]


def get_parsed_event(event):
    if type(event) == type({}):
        parsed_event = event
    else:
        parsed_event = json.loads(event)
        
    ecs_service_count_override = parsed_event.get("ecs_service_count_override")
    action_type = parsed_event.get("ActionType")

    if not parsed_event.get("ResourceArn") and not parsed_event.get("TagValue"):
        raise Exception(f"Please enter a tag value or a resource arn")

    if parsed_event.get("ResourceArn") and parsed_event.get("TagValue"):
        raise Exception(f"Please pick either tag value or resource arn")

    if not action_type or not action_type in ACCEPTED_ACTIONS:
        raise Exception(f"Please enter a valid action type: {ACCEPTED_ACTIONS.join(' or')}")

    if ecs_service_count_override:
        for key in ecs_service_count_override:
            service_override = ecs_service_count_override[key]
            if not service_override.get("min_task_count") or not service_override.get("desired_task_count"):
                raise Exception(f"Please enter min_task_count and desired_task_count for service {key}")

    return parsed_event


def has_matching_tags(resource_tags, tag_key, tag_value):
    matched_tags = [x for x in resource_tags if x["Key"] == tag_key and x["Value"] == tag_value]
    has_tag_match = len(matched_tags) > 0
    return has_tag_match


def update_ecs_service(region, cluster_name, service_name, min_tasks, desired_tasks):
    aas_client = boto3.client("application-autoscaling", region_name=region)
    ecs_client = boto3.client("ecs", region_name=region)

    service_resource_id = f"service/{cluster_name}/{service_name}"

    auto_scaler_response = aas_client.describe_scalable_targets(ServiceNamespace="ecs", ResourceIds=[service_resource_id])
    has_auto_scaling = len(auto_scaler_response["ScalableTargets"]) > 0

    if has_auto_scaling:
        print(f"Updating {service_name} Auto Scaling MinCapacity to {min_tasks}")
        aas_client.register_scalable_target(
            ServiceNamespace="ecs",
            ResourceId=service_resource_id,
            ScalableDimension="ecs:service:DesiredCount",
            MinCapacity=min_tasks,
        )

    print(f"Updating {service_name} to {desired_tasks} desired tasks")
    ecs_client.update_service(cluster=cluster_name, service=service_name, desiredCount=desired_tasks)


def update_ecs(region, action_type, tag_value, resource_arn, ecs_service_count_override):
    ecs_client = boto3.client("ecs", region_name=region)

    cluster_list = ecs_client.list_clusters()
    for cluster_arn in cluster_list["clusterArns"]:
        # get cluster name
        cluster_desc = ecs_client.describe_clusters(clusters=[cluster_arn])
        cluster_name = cluster_desc["clusters"][0]["clusterName"]

        # list services
        service_list = ecs_client.list_services(cluster=cluster_arn)
        service_arns = service_list["serviceArns"]

        for service_arn in service_arns:
            # check if service has scheduler tag
            if len(service_arns):
                resource_tags_list = get_resource_tags(service_arn, region)
                tag_key = get_tag_from_type(action_type)
                has_tag_match = has_matching_tags(resource_tags_list, tag_key, tag_value)

            if has_tag_match or service_arn == resource_arn:
                print(f"Found matching tag or arn in {service_arn}")
                service_desc = ecs_client.describe_services(cluster=cluster_arn, services=[service_arn])
                service_name = service_desc["services"][0]["serviceName"]

                if action_type == "START":
                    desired_task_count = 1
                    min_task_count = 1
                else:
                    desired_task_count = 0
                    min_task_count = 0

                if service_name in ecs_service_count_override:
                    print("Using custom service counts")
                    min_task_count = ecs_service_count_override[service_name]["min_task_count"]
                    desired_task_count = ecs_service_count_override[service_name]["desired_task_count"]

                update_ecs_service(
                    region,
                    cluster_name,
                    service_name,
                    min_task_count,
                    desired_task_count,
                )


def update_rds(region, action_type, tag_value, resource_arn):
    client = boto3.client("rds", region_name=region)
    response = client.describe_db_instances()

    tag_key = get_tag_from_type(action_type)

    v_readReplica = []
    for i in response["DBInstances"]:
        readReplica = i["ReadReplicaDBInstanceIdentifiers"]
        v_readReplica.extend(readReplica)

    for i in response["DBInstances"]:
        if i["Engine"] not in ["aurora-mysql", "aurora-postgresql"]:
            arn = i["DBInstanceArn"]

            resp2 = client.list_tags_for_resource(ResourceName=arn)
            has_tag_match = has_matching_tags(resp2["TagList"], tag_key, tag_value)

            if has_tag_match or arn == resource_arn:
                print(f"Found matching tag or arn in {i['DBInstanceIdentifier']}")

                if (i["DBInstanceIdentifier"] in v_readReplica or len(i["ReadReplicaDBInstanceIdentifiers"]) != 0):
                    print(f'DB Instance {i["DBInstanceIdentifier"]} is or has a Read Replica.')
                elif i["DBInstanceStatus"] == "available" and action_type == "STOP":
                    print(f'Stopping DB Instance {i["DBInstanceIdentifier"]}')
                    client.stop_db_instance(DBInstanceIdentifier=i["DBInstanceIdentifier"])
                elif i["DBInstanceStatus"] == "stopped" and action_type == "START":
                    print(f'Starting DB Instance {i["DBInstanceIdentifier"]}')
                    client.start_db_instance(DBInstanceIdentifier=i["DBInstanceIdentifier"])
                else:
                    print(f'DB Instance {i["DBInstanceIdentifier"]} is in {i["DBInstanceStatus"]} state')
                    
    response = client.describe_db_clusters()
    for i in response["DBClusters"]:
        cluarn = i["DBClusterArn"]
        resp2 = client.list_tags_for_resource(ResourceName=cluarn)
        has_tag_match = has_matching_tags(resp2["TagList"], tag_key, tag_value)

        if has_tag_match or arn == resource_arn:
            print(f"Found matching tag or arn in {i['DBClusterIdentifier']}")

            if i["Status"] == "available" and action_type == "STOP":
                print(f'Stopping Cluster Cluster {i["DBClusterIdentifier"]}')
                client.stop_db_cluster(DBClusterIdentifier=i["DBClusterIdentifier"])
            elif i["Status"] == "stopped" and action_type == "START":
                print(f'Starting Cluster Cluster {i["DBClusterIdentifier"]}')
                client.start_db_cluster(DBClusterIdentifier=i["DBClusterIdentifier"])
            else:
                print(f'Cluster {i["DBClusterIdentifier"]} is in {i["Status"]} state')


def main(event, lambdaContext): #lambda context is passed as an argument by the lambda handler but is not used in this application
    print("Starting scheduler...")
    print(event)
    event_json = get_parsed_event(event)

    action_type = event_json["ActionType"] #action type START or STOP

    resource_arn = event_json.get("ResourceArn", None) #instead of searching by tags, you can pick a specific resource by its ARN
    tag_value = event_json.get("TagValue", None)
    ecs_service_count_override = event_json.get("EcsServiceCountOverride", {}) #used to pick specific min and desired task amount

    for region in REGIONS:
        update_ecs(
            region, action_type, tag_value, resource_arn, ecs_service_count_override
        )
        update_rds(region, action_type, tag_value, resource_arn)
