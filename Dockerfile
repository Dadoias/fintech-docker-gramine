FROM gramineproject/gramine

RUN apt update && apt install -y python3.9 python3.9-dev make 
RUN apt install -y python3-pip
RUN gramine-sgx-gen-private-key

RUN mkdir -p /fintech/fintech_ex
COPY Makefile python.manifest.template /fintech/

WORKDIR /fintech/fintech_ex
COPY ./fintech_ex/* ./

RUN pip install -r requirements.txt

WORKDIR /fintech
RUN make SGX=1

EXPOSE 9443
EXPOSE 944

CMD ["gramine-sgx ./python fintech_ex/fintech_server.py"]


