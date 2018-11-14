FROM python:3-alpine

ADD requirements.txt /ebooks/

WORKDIR /ebooks/
VOLUME /ebooks/data/

RUN apk add --virtual .build-deps gcc musl-dev libffi-dev openssl-dev \
 && pip install -r requirements.txt \
 && apk del --purge .build-deps \
 && ln -s data/config.json . \
 && ln -s data/toots.db .

ADD *.py /ebooks/

RUN (echo "*/30 * * * * cd /ebooks/ && python gen.py"; \
     echo "5 */2 * * * cd /ebooks/ && python main.py"; \
     echo "@reboot cd /ebooks/ && python reply.py") | crontab -

ENV ebooks_site=https://botsin.space

CMD (test -f data/config.json || echo "{\"site\":\"${ebooks_site}\"}" > data/config.json) \
 && (test -f data/toots.db || (python main.py && exit)) \
 && exec crond -f -L /dev/stdout
