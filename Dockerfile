FROM gramineproject/gramine:v1.5

RUN apt update && apt install -y software-properties-common && add-apt-repository ppa:deadsnakes/ppa && apt-get upgrade -y
RUN apt install -y python3.9 python3.9-dev make && apt install -y python3-pip
RUN gramine-sgx-gen-private-key

RUN mkdir -p /fintech/fintech_ex
COPY Makefile python.manifest.template /fintech/

WORKDIR /fintech/fintech_ex
COPY ./fintech_ex/* ./

RUN python3.9 -m pip install -r requirements.txt

WORKDIR /fintech
RUN make SGX=1

EXPOSE 9443
EXPOSE 944

CMD ["gramine-sgx ./python fintech_ex/fintech_server.py"]
#CMD ["python3 ./fintech_ex/test.py"]

