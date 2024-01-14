ARG base_image=debian:bookworm

FROM ${base_image}

ENV LC_ALL C
ENV container docker
ENV DEBIAN_FRONTEND noninteractive

RUN dpkg --add-architecture i386
RUN rm --force /etc/apt/sources.list
COPY files/etc/apt/sources.list.d/debian.sources /etc/apt/sources.list.d/debian.sources
RUN apt-mark showmanual | xargs --no-run-if-empty -- apt-mark auto --
RUN apt update --assume-yes && apt install --assume-yes apt-utils
RUN apt update --assume-yes && apt full-upgrade --assume-yes

RUN echo locales locales/locales_to_be_generated select en_US.UTF-8 UTF-8 | debconf-set-selections
RUN echo locales locales/default_environment_locale select en_US.UTF-8 | debconf-set-selections
RUN apt update --assume-yes && apt install --assume-yes locales

RUN apt update --assume-yes && apt install --assume-yes python3

RUN apt update --assume-yes && apt install --assume-yes libsdl2-dev:i386
RUN echo steam steam/license note '' | debconf-set-selections
RUN echo steam steam/question select "I AGREE" | debconf-set-selections
RUN apt update --assume-yes && apt install --assume-yes steamcmd

COPY files/usr/local/bin/entry_point.py /usr/local/bin/entry_point
RUN chmod +x /usr/local/bin/entry_point

RUN apt update --assume-yes && apt --assume-yes full-upgrade && apt autoremove --assume-yes && apt purge --assume-yes '~c'
RUN apt clean --assume-yes && for _path in /tmp /var/tmp /var/lib/apt/lists; do \
      find "${_path}" -mindepth 1 -maxdepth 1 -exec rm --force --recursive -- {} \;; \
    done

ENTRYPOINT ["/usr/local/bin/entry_point"]
