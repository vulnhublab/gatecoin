
# This will build the latest master
#
# we use an intermediate image to build this image. it will make the resulting
# image a bit smaller.
#
# you can build the image with:
#
#   docker build . -t gatecoin

FROM python:3.9 as builder

# use --build-arg GATECOINVERSION=v0.0.3 to build a specific (tagged) version
ARG REPO=gatecoin/gatecoin
ARG GATECOINVERSION=develop

# This is a "hack" to automatically invalidate the cache in case there are new commits
ADD https://api.github.com/repos/${REPO}/commits/${GATECOINVERSION} /dev/null

# clone gatecoin repo + install dependencies
RUN git clone -b ${GATECOINVERSION} https://github.com/${REPO} /app/gatecoin

RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app/gatecoin

RUN make install


FROM python:3.9-slim as runner

COPY --from=builder /opt/venv /opt/venv

EXPOSE 5001

ENTRYPOINT ["/opt/venv/bin/python3", "-m", "gatecoin"]
