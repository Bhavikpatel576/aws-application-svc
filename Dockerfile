#local development
FROM base_stage_app_svc
COPY ./requirements.txt /opt/app/
RUN pip install -r /opt/app/requirements.txt
ENTRYPOINT ["/opt/startup/startup.sh"]
