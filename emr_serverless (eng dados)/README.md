# EMR Serverless Pipeline

Aqui você encontra os códigos para as configurações iniciais de uma aplicação EMR serverless para um job Apache Spark


- Criação da Venv com os módulos pythons necessários para o projeto (Dockerfile)
    - Para utilizar os módulos python dentro do emr serverless é necessário utilizar um Venv com esses módulos instalados, é importante frizar que o venv deve ser criado na base **linux/amd64 amazonlinux:2**.

    - Depois de criado, o arquivo **.tar.gz** deve ser disponibilizado no bucket do projeto no S3

- Disponibilização dos módulos custom par ao S3 via GH Actions (push_modules.yaml)

    - Todo o código do seu projeto deve ser zipado (.zip) e disponibilizado também no S3

- Arquivo **main.py**
    - O arquivo **main.py** é quem vai receber as flags passadas no pipeline e passará para o código principal
    - O aquivo main.py também deve ser disponibilizado no bucket do projeto (push_main.yaml)

- Pipeline
    - O código do pipeline está disponivel no arquivo **pipeline.py**
    - Nos parametros de configuração do job devem ser colcoados os path para cada um dos arquivos criados (pyspark_venv.tar.gz, modules.zip e main.py)

- Providers da AWS
    - Para utilizar os operadores é necessário configurar os providers da AWS na seu airflow

    ``` 
        FROM apache/airflow:2.5.1-python3.10
        RUN pip install --no-cache-dir \    
        apache-airflow-providers-amazon \
    ```