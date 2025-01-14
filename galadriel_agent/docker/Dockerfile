FROM h4n00/galadriel_base:latest

RUN yum update && yum install -y gcc logrotate g++ git 

# Logrotate
COPY docker/logrotate_logs /etc/logrotate.d/log-file
RUN chmod 644 /etc/logrotate.d/log-file

# Create new user to not run in sudo mode
RUN useradd --create-home appuser
WORKDIR /home/appuser

COPY . /home/appuser

RUN pip install -e .
