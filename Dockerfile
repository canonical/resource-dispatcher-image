FROM public.ecr.aws/ubuntu/ubuntu:24.04
ARG VERSION

ENV TZ=UTC

RUN set -eux; \
    # install python
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get full-upgrade -y; \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    tzdata; \
    DEBIAN_FRONTEND=noninteractive apt-get remove --purge --auto-remove -y; \
    rm -rf /var/lib/apt/lists/*
# security team requirement
RUN mkdir -p /usr/share/rocks; \
    (echo "# os-release" && cat /etc/os-release && echo "# dpkg-query" && dpkg-query -f '${db:Status-Abbrev},${binary:Package},${Version},${source:Package},${Source:Version}\n' -W) > /usr/share/rocks/dpkg.query

WORKDIR /app
COPY requirements.txt /app
RUN set -eux; \
    pip3 install -r requirements.txt --no-cache-dir

COPY ./resource_dispatcher /app 

EXPOSE 80
CMD ["python3", "main.py"]