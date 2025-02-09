#!/bin/bash

# Konfigurera LXC container för JVH pussel-sida
# Kör detta script på Proxmox hosten

# Variabler
CT_ID="200"  # Container ID
CT_NAME="jvh-puzzles"
CT_PASSWORD="dittlösenord"
STORAGE="local"  # Anpassa till önskad storage
CT_TEMPLATE="debian-12-standard_12.2-1_amd64.tar.xz"

# Skapa container
pct create $CT_ID $STORAGE:vztmpl/$CT_TEMPLATE \
    --hostname $CT_NAME \
    --password $CT_PASSWORD \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --cores 1 \
    --memory 512 \
    --swap 512 \
    --rootfs $STORAGE:8

# Starta container
pct start $CT_ID

# Vänta på att containern ska starta
sleep 10

# Hämta tilldelad IP-adress
CT_IP=$(pct exec $CT_ID -- ip -4 addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

# Installera nödvändiga paket
pct exec $CT_ID -- bash -c "apt update && apt install -y python3-pip python3-venv git nginx supervisor"

# Skapa användare och mapp för applikationen
pct exec $CT_ID -- bash -c "
    useradd -m -s /bin/bash jvh
    mkdir -p /opt/jvh
    chown jvh:jvh /opt/jvh
"

# Klona repository och sätt upp miljön
pct exec $CT_ID -- bash -c "
    cd /opt/jvh
    git clone https://github.com/din-repo/JVH.git
    cd JVH
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
"

# Konfigurera Nginx
pct exec $CT_ID -- bash -c "cat > /etc/nginx/sites-available/jvh << 'EOL'
server {
    listen 80;
    server_name _;

    location /static/ {
        root /opt/jvh/JVH;
    }

    location /media/ {
        root /opt/jvh/JVH;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL"

# Aktivera Nginx konfiguration
pct exec $CT_ID -- bash -c "
    ln -s /etc/nginx/sites-available/jvh /etc/nginx/sites-enabled/
    rm /etc/nginx/sites-enabled/default
    systemctl restart nginx
"

# Konfigurera Supervisor
pct exec $CT_ID -- bash -c "cat > /etc/supervisor/conf.d/jvh.conf << 'EOL'
[program:jvh]
command=/opt/jvh/JVH/venv/bin/gunicorn JVH.wsgi:application --bind 127.0.0.1:8000
directory=/opt/jvh/JVH
user=jvh
autostart=true
autorestart=true
stderr_logfile=/var/log/supervisor/jvh.err.log
stdout_logfile=/var/log/supervisor/jvh.out.log
EOL"

# Starta om Supervisor
pct exec $CT_ID -- bash -c "
    supervisorctl reread
    supervisorctl update
    supervisorctl restart all
"

# Skapa separata databaser
pct exec $CT_ID -- bash -c "
    cd /opt/jvh/JVH
    source venv/bin/activate
    python manage.py makemigrations
    python manage.py migrate --database=default
    python manage.py migrate --database=puzzles_db
"

echo "Installation klar! Sidan är nu tillgänglig på http://$CT_IP"
