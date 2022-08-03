# FROM osgeo/gdal
# FROM python:3.8-alpine

FROM public.ecr.aws/lambda/python:3.8
RUN yum update -y
RUN yum install -y wget mesa-libGL zip libpq-dev gcc
# RUN yum install unzip
# RUN wget https://github.com/Badar97/Progetto_PA/raw/main/file.zip
# RUN unzip file.zip
RUN wget https://netcologne.dl.sourceforge.net/project/gdal-wheels-for-linux/GDAL-3.4.1-cp38-cp38-manylinux_2_5_x86_64.manylinux1_x86_64.whl
RUN pip install GDAL-3.4.1-cp38-cp38-manylinux_2_5_x86_64.manylinux1_x86_64.whl \
    shapely==1.8.2 \
#    geopandas==0.10.2 \
    geopandas \
    matplotlib \
    numpy \
    opencv-python \
    requests \
    psycopg2-binary
#WORKDIR /app
WORKDIR ${LAMBDA_TASK_ROOT}

COPY app.py ${LAMBDA_TASK_ROOT}
COPY chaintick.py ${LAMBDA_TASK_ROOT}
COPY elevation_analysis.py ${LAMBDA_TASK_ROOT}
CMD ["app.handler"]