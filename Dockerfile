FROM python:3.6
WORKDIR /app
COPY . . 
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
ENV APP_FLASK=app.py
RUN mkdir -p /var/log/zoom-dashboard /etc/zoom-dashboard
#CMD /app/dispatch_collectors.sh

