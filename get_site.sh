#!/bin/bash

# Kontrollera om scriptet körs i en LXC container
if [ -f /proc/1/environ ] && grep -q "container=lxc" /proc/1/environ; then
    echo "Kör uppdatering i LXC containern..."
    
    # Gå till projektmappen
    cd /opt/jvh/JVH

    # Aktivera virtual environment
    source venv/bin/activate

    # Spara eventuella lokala ändringar
    git stash

    # Hämta senaste versionen från GitHub
    git pull origin main

    # Återställ eventuella lokala ändringar
    git stash pop

    # Uppdatera dependencies
    pip install -r requirements.txt
    apt-get update
    apt-get install -y chromium-chromedriver
   

    # Kör migrations
    python manage.py makemigrations
    python manage.py migrate --database=default
    python manage.py migrate --database=puzzles_db

    # Skapa/uppdatera superuser
    python manage.py create_admin_user

    # Samla statiska filer
    python manage.py collectstatic --noinput

    # Sätt rätt rättigheter på databasfilerna
    chown -R jvh:jvh .
    chmod 664 db.sqlite3
    chmod 664 puzzles.sqlite3
    chmod 775 .
    chmod 775 $(dirname db.sqlite3)
    chmod 775 $(dirname puzzles.sqlite3)

    # Starta om tjänsterna
    supervisorctl restart jvh
    systemctl restart nginx

    echo "Uppdatering klar!"
    exit 0
fi

# Konfigurera LXC container för JVH pussel-sida
# Kör detta script på Proxmox hosten

# Funktion för att kontrollera om ett kommando lyckas
check_command() {
    if [ $? -ne 0 ]; then
        echo "Fel: $1"
        exit 1
    fi
}

# Variabler
CT_ID="200"  # Container ID
CT_NAME="jvh-puzzles"
CT_PASSWORD="JVHpassword123"  # Minst 5 tecken långt lösenord
STORAGE="Store"  # Storage för container
TEMPLATE_STORAGE="local"  # Storage för templates
CT_TEMPLATE="debian-12-standard_12.2-1_amd64.tar.zst"

# Kontrollera om containern redan finns
if pct status $CT_ID >/dev/null 2>&1; then
    echo "En container med ID $CT_ID finns redan. Välj ett annat ID."
    exit 1
fi

# Uppdatera template-listan
echo "Uppdaterar template-listan..."
pveam update
check_command "Kunde inte uppdatera template-listan"

# Kontrollera om template finns och ladda ner vid behov
echo "Kontrollerar template..."
if ! pveam list $TEMPLATE_STORAGE | grep -q "$CT_TEMPLATE"; then
    echo "Laddar ner template..."
    pveam download $TEMPLATE_STORAGE $CT_TEMPLATE
    check_command "Kunde inte ladda ner template"
fi

echo "Skapar container..."
# Skapa container
pct create $CT_ID "$TEMPLATE_STORAGE:vztmpl/$CT_TEMPLATE" \
    --hostname $CT_NAME \
    --password "$CT_PASSWORD" \
    --net0 name=eth0,bridge=vmbr0,ip=dhcp \
    --cores 1 \
    --memory 512 \
    --swap 512 \
    --rootfs $STORAGE:8
check_command "Kunde inte skapa container"

echo "Startar container..."
# Starta container
pct start $CT_ID
check_command "Kunde inte starta container"

# Vänta på att containern ska starta och få en IP-adress
echo "Väntar på att containern ska starta..."
for i in {1..30}; do
    sleep 2
    CT_IP=$(pct exec $CT_ID -- ip -4 addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
    if [ ! -z "$CT_IP" ]; then
        break
    fi
done

if [ -z "$CT_IP" ]; then
    echo "Kunde inte få IP-adress från containern"
    exit 1
fi

echo "Container IP: $CT_IP"

echo "Installerar paket..."
# Installera nödvändiga paket
pct exec $CT_ID -- bash -c "apt update && apt install -y python3-pip python3-venv git nginx supervisor"
check_command "Kunde inte installera paket"

echo "Skapar användare och mappar..."
# Skapa användare och mapp för applikationen
pct exec $CT_ID -- bash -c "
    useradd -m -s /bin/bash jvh
    mkdir -p /opt/jvh
    chown jvh:jvh /opt/jvh
"
check_command "Kunde inte skapa användare och mappar"

echo "Klonar repository och sätter upp miljön..."
# Klona repository och sätt upp miljön
pct exec $CT_ID -- bash -c "
    cd /opt/jvh
    git clone https://github.com/kmhbg/JVH.git
    cd JVH
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
"
check_command "Kunde inte klona repository eller sätta upp miljön"

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

# Skapa separata databaser och superuser
pct exec $CT_ID -- bash -c "
    cd /opt/jvh/JVH
    source venv/bin/activate
    python manage.py makemigrations
    python manage.py migrate --database=default
    python manage.py migrate --database=puzzles_db
    python manage.py create_admin_user
"
check_command "Kunde inte skapa databaser eller superuser"

# Efter att databaserna skapats, sätt rätt rättigheter
pct exec $CT_ID -- bash -c "
    cd /opt/jvh/JVH
    chown -R jvh:jvh .
    chmod 664 db.sqlite3
    chmod 664 puzzles.sqlite3
    chmod 775 .
    chmod 775 $(dirname db.sqlite3)
    chmod 775 $(dirname puzzles.sqlite3)
"
check_command "Kunde inte sätta rättigheter på databasfilerna"

echo "Installation klar! Sidan är nu tillgänglig på http://$CT_IP"

# Skapa och kör migrationer
python manage.py makemigrations
python manage.py migrate --database=default
python manage.py migrate --database=puzzles_db

# Skapa superuser om den inte finns
echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'admin123') if not User.objects.filter(username='admin').exists() else None" | python manage.py shell

# Importera pussel
python manage.py import_puzzles

# Sätt rättigheter på databasfilerna
chown -R jvh:jvh .
chmod 664 db.sqlite3
chmod 664 puzzles.sqlite3
chmod 775 .
chmod 775 $(dirname db.sqlite3)
chmod 775 $(dirname puzzles.sqlite3)
