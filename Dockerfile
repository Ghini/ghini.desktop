# Dockerfile

#
#
#  Configuration is stored in $HOME/.bauble/config
#
#  Build: docker buildx build --load -t ghini-desktop .
#  Run:   docker run --rm -it ghini-desktop
# docker run --rm -it   -e USER=$(id -un)   -e DISPLAY=$DISPLAY   -e DB_HOST=postgres.wysechoice.net   -e DB_PORT=5432   -e DB_NAME=ghini_test3   -e DB_USER=ghini   -e DB_SSLMODE=prefer   -e KRB5_CONFIG=/krb5/krb5.conf   -e KRB5_CLIENT_KTNAME=/krb5/krb5.keytab   -v /tmp/.X11-unix:/tmp/.X11-unix   -v $HOME/krb5:/krb5:ro   -v $HOME:$HOME -v$HOME/.bauble:$HOME/.bauble ghini-desktop bash -c "ghini"
#

# Stage 1: Build Stage
FROM debian:bullseye AS build

# Set environment variables to suppress debconf warnings
ENV DEBIAN_FRONTEND=noninteractive

# Set up environment variables
ENV HOME=/root
ENV LINE=ghini-3.1
ENV VIRTUAL_ENV=/root/.virtualenvs/$LINE
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV USER=root

# Install necessary system packages for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gettext \
    git \
    pkg-config \
    python3 \
    python3-dev \
    python3-venv \
    libpython3-dev \
    libjpeg-dev \
    libpq-dev \
    libxslt1-dev \
    zlib1g-dev \
    libcairo2 \
    libcairo2-dev \
    libgirepository1.0-dev \
    gir1.2-gtk-3.0 \
    gir1.2-gtkclutter-1.0 \
    gir1.2-champlain-0.12 \
    gir1.2-gtkchamplain-0.12 \
    krb5-user \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

# Clone ghini.desktop repository
RUN mkdir -p $HOME/Local/github/Ghini \
    && cd $HOME/Local/github/Ghini \
    && git clone -b $LINE https://github.com/Ghini/ghini.desktop.git

# Set the working directory to the cloned repository
WORKDIR $HOME/Local/github/Ghini/ghini.desktop

# Create and activate virtual environment, install dependencies
RUN python3 -m venv $VIRTUAL_ENV \
    && . $VIRTUAL_ENV/bin/activate \
    && pip install --upgrade pip wheel \
    && pip install 'setuptools<58.0.0' \
    && pip install PyGObject \
    && pip install psycopg2 \
    && pip install . \
    && rm -rf $HOME/.cache/pip

# Stage 2: Runtime Stage
FROM debian:bullseye

# Set environment variables to suppress debconf warnings
ENV DEBIAN_FRONTEND=noninteractive

# Set up environment variables
ENV HOME=/root
ENV LINE=ghini-3.1
ENV VIRTUAL_ENV=/root/.virtualenvs/$LINE
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV USER=root

# Install necessary system packages for runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    libpython3.9 \
    libjpeg62-turbo \
    libpq5 \
    libxslt1.1 \
    zlib1g \
    libcairo2 \
    libgirepository-1.0-1 \
    gir1.2-gtk-3.0 \
    gir1.2-gtkclutter-1.0 \
    gir1.2-champlain-0.12 \
    gir1.2-gtkchamplain-0.12 \
    krb5-user \
    libkrb5-3 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from build stage
COPY --from=build $VIRTUAL_ENV $VIRTUAL_ENV

# Copy application code from build stage
COPY --from=build /root/Local/github/Ghini/ghini.desktop /app

# Set the working directory
WORKDIR /app

# Set entrypoint
CMD ["ghini"]
