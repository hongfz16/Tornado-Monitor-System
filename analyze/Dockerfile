# FROM python:3.7

FROM python3-opencv3:latest

RUN apt-get update && \
        apt-get install -y \
        build-essential \
        cmake \
        git \
        wget \
        unzip \
        yasm \
        pkg-config \
        libswscale-dev \
        libtbb2 \
        libtbb-dev \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libavformat-dev \
        libpq-dev \
        gfortran \
        wget \
        curl \
        graphicsmagick \
        libgraphicsmagick1-dev \
        libatlas-dev \
        libavcodec-dev \
        libgtk2.0-dev \
        liblapack-dev \
        python3-dev \
        python3-numpy \
        software-properties-common \
        zip \
        && apt-get clean && rm -rf /tmp/* /var/tmp/*

# RUN pip install numpy

# WORKDIR /
# ENV OPENCV_VERSION="3.4.2"
# RUN wget https://github.com/opencv/opencv/archive/${OPENCV_VERSION}.zip \
    # && unzip ${OPENCV_VERSION}.zip \
    # && mkdir /opencv-${OPENCV_VERSION}/cmake_binary \
    # && cd /opencv-${OPENCV_VERSION}/cmake_binary \
    # && cmake -DBUILD_TIFF=ON \
    #   -DBUILD_opencv_java=OFF \
    #   -DWITH_CUDA=OFF \
    #   -DWITH_OPENGL=ON \
    #   -DWITH_OPENCL=ON \
    #   -DWITH_IPP=ON \
    #   -DWITH_TBB=ON \
    #   -DWITH_EIGEN=ON \
    #   -DWITH_V4L=ON \
    #   -DBUILD_TESTS=OFF \
    #   -DBUILD_PERF_TESTS=OFF \
    #   -DCMAKE_BUILD_TYPE=RELEASE \
    #   -DCMAKE_INSTALL_PREFIX=$(python3.7 -c "import sys; print(sys.prefix)") \
    #   -DPYTHON_EXECUTABLE=$(which python3.7) \
    #   -DPYTHON_INCLUDE_DIR=$(python3.7 -c "from distutils.sysconfig import get_python_inc; print(get_python_inc())") \
    #   -DPYTHON_PACKAGES_PATH=$(python3.7 -c "from distutils.sysconfig import get_python_lib; print(get_python_lib())") \
    #   .. \
    # && make -j8 install \
    # && rm /${OPENCV_VERSION}.zip \
    # && rm -r /opencv-${OPENCV_VERSION} \
RUN cd ~ && \
    mkdir -p dlib && \
    git clone -b 'v19.9' --single-branch https://github.com/davisking/dlib.git dlib/ && \
    cd  dlib/ && \
    python3 setup.py install --yes USE_AVX_INSTRUCTIONS

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /usr/src/app
CMD ["python3", "-u", "analyze.py"]