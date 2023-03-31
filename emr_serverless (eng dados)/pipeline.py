from datetime import datetime, timedelta

from airflow import DAG
from airflow.providers.amazon.aws.operators.ecs import EcsRunTaskOperator
from airflow.providers.amazon.aws.operators.emr import (
    EmrServerlessCreateApplicationOperator,
    EmrServerlessDeleteApplicationOperator,
    EmrServerlessStartJobOperator
)


JOB_ROLE_ARN = 'arn:aws:iam::<aws_acc_id>:role/<role_name>'
TENANT = 'tenant-name'
ENV = 'dev'/'prod'
S3_LOGS_BUCKET = f's3://bucket-name/{TENANT}/{ENV}/logs'
DEFAULT_MONITORING_CONFIG = {
    "monitoringConfiguration": {
        "s3MonitoringConfiguration": {"logUri": S3_LOGS_BUCKET}
    },
}
model = [str({'job_name': 'job', 'tenant': TENANT, 'env': ENV, 'flag_1': 'Value', 'flag_2': 'Value'})]

jobs = [] 

steps_for_process = {
    'model': model
}


default_args = {
		'owner': 'Owner_name',
		'start_date': datetime(2022, 3, 4),
		'retries': 0,
		'retry_delay': timedelta(minutes=5)
}


product = DAG('product_pipeline',
		default_args=default_args,
		description='Dag description',
		schedule_interval=None,
		catchup=False,
		tags=["tags"]
		)

create_app = EmrServerlessCreateApplicationOperator(
		task_id="create_spark_app",
		job_type="SPARK",
		release_label="emr-6.6.0",
		config={"name": "product-pipeline"},
		dag = product
	)

application_id = create_app.output
for name, step_config in steps_for_process.items():
	jobs.append(
		EmrServerlessStartJobOperator(
			task_id= name,
			application_id=application_id,
			execution_role_arn=JOB_ROLE_ARN,
			dag = product,
			job_driver={
				"sparkSubmit": {
					"entryPoint": f"s3://bucket_name/folder/main.py",
					"entryPointArguments": step_config,
					"sparkSubmitParameters": "--conf spark.submit.pyFiles=s3://bucket_name/folder/modules.zip --conf spark.archives=s3://bucket_name/folder/pyspark_venv.tar.gz#environment  --conf spark.emr-serverless.driverEnv.PYSPARK_DRIVER_PYTHON=./environment/bin/python --conf spark.emr-serverless.driverEnv.PYSPARK_PYTHON=./environment/bin/python --conf spark.executorEnv.PYSPARK_PYTHON=./environment/bin/python"
				}
			},
			configuration_overrides=DEFAULT_MONITORING_CONFIG,
		)
	)

delete_app = EmrServerlessDeleteApplicationOperator(
	task_id="delete_app",
	application_id=application_id,
	trigger_rule="all_done",
	dag = product
)


create_app >> jobs[0] >> delete_app