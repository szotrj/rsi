FROM centos:7
RUN yum update -y && \
    yum install -y epel-release python36 python36-pip python36-devel
# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt
WORKDIR /app
RUN pip3 install -r requirements.txt
COPY src /app
ENTRYPOINT [ "python3" ]
CMD [ "app.py" ]
