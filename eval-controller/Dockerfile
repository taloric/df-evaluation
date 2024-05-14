# evaluation
#
# VERSION               1.0.0

# 构建层
FROM hub.deepflow.yunshan.net/dev/python:3.8.19-slim-bullseye AS builder
RUN apt-get update && \
    apt-get install --no-install-suggests \
    --no-install-recommends --yes \
    python3-venv=3.9.2-3 \
    build-essential=12.9 \
    gcc=4:10.2.1-1 \
    libpython3-dev=3.9.2-3 \
    libpq-dev=13.14-0+deb11u1 \
    default-libmysqlclient-dev=1.0.7 \
    libmariadb-dev=1:10.5.23-0+deb11u1 \
    libmariadb3=1:10.5.23-0+deb11u1 \
    make=4.3-4.1 \
    && \
    python3 -m venv /root/venv && \
    /root/venv/bin/pip install -U pip==24.0
# 安装 Base pip 依赖包
FROM builder AS builder-venv-base
RUN /root/venv/bin/pip install cffi==1.16.0 --trusted-host mirrors.aliyun.com --index-url https://mirrors.aliyun.com/pypi/simple/
# 安装自定义 pip 依赖包
FROM builder-venv-base AS builder-venv-custom
COPY requirements.txt /root/requirements.txt
RUN /root/venv/bin/pip install --disable-pip-version-check \
        --no-cache-dir \
        --trusted-host mirrors.aliyun.com \
        --index-url https://mirrors.aliyun.com/pypi/simple/ \
        -r /root/requirements.txt

# 最终运行层
FROM hub.deepflow.yunshan.net/dev/python:3.8.19-slim-bullseye AS runner
ARG TARGETARCH
RUN --mount=type=bind,target=/temp,from=builder-venv-custom,source=/ \
    BUILD_ARCH=$(echo ${TARGETARCH}|sed 's|amd64|x86_64|'|sed 's|arm64|aarch64|') && \
    cp -raf /temp/usr/lib/${BUILD_ARCH}-linux-gnu/libmariadb.* /usr/lib/${BUILD_ARCH}-linux-gnu/ && \
    cp -raf /temp/usr/lib/${BUILD_ARCH}-linux-gnu/libmariadb3/ /usr/lib/${BUILD_ARCH}-linux-gnu/libmariadb3/ && \
    cp -raf /temp/usr/lib/${BUILD_ARCH}-linux-gnu/libmysql* /usr/lib/${BUILD_ARCH}-linux-gnu/ && \
    cp -raf /temp/root/venv /root/venv && \
    apt-get update && \
    apt-get install --no-install-suggests \
    --no-install-recommends --yes \
    vim-tiny=2:8.2.2434-3+deb11u1 curl=7.74.0-1.3+deb11u11
# 复制代码
COPY ./etc/eval-controller.yaml /etc/
COPY ./eval-controller/ /root/eval-controller/
# Run
CMD /root/venv/bin/python3 -u /root/eval-controller/eval-controller.py