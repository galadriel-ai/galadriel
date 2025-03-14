FROM galadrielai/galadriel_base:latest

# Logrotate
COPY docker/logrotate_logs /etc/logrotate.d/log-file
RUN chmod 644 /etc/logrotate.d/log-file

# Create new user to not run in sudo mode
RUN useradd --create-home appuser
WORKDIR /home/appuser

COPY . /home/appuser

RUN python3.12 -m pip install -e .
