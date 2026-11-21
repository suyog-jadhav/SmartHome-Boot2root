FROM alpine:3.16

# Copy vulnerable OpenSSH packages
COPY openssh/ /tmp/openssh/

# Install required dependency
RUN apk add --no-cache libedit

# Install the vulnerable OpenSSH packages
RUN apk add --no-network /tmp/openssh/*.apk \
    && rm -rf /tmp/openssh

# Create the SSH target user
RUN adduser -D -s /bin/sh automation

# Prepare SSH
RUN mkdir -p /run/sshd \
    && ssh-keygen -A

# Configure SSH
RUN sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config \
    && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

CMD ["/bin/sh"]