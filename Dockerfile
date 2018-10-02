FROM python:3.5.2-slim

# set the working directory in the container to /app
WORKDIR /app

# add the current directory to the container as /app
COPY . /app

# execute everyone's favorite pip command, pip install -r
RUN pip install --trusted-host pypi.tuna.tsinghua.edu.cn -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# unblock port 80 for the Flask app to run on
EXPOSE 5000

# execute the Flask app
CMD ["python", "app.py"]
