FROM --platform=linux/amd64 amazonlinux:2 AS base

RUN yum install -y python3
RUN yum install -y gcc
RUN yum install -y python3-devel

COPY requirements.txt requirements.txt

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install -r requirements.txt && \
    python3 -m pip install \
    venv-pack==0.2.0


RUN mkdir /output && venv-pack -o /output/pyspark_venv.tar.gz

FROM scratch AS export
COPY --from=base /output/pyspark_venv.tar.gz /