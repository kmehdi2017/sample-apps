FROM python:3.6

RUN apt-get update 

COPY . /
WORKDIR ./

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 5000
CMD [ "python", "khan_crypto.py" ]