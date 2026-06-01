server {
    server_name retire.barrettafamily.com;

    location / {
        proxy_pass http://127.0.0.1:8002;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/ubuntu/AnthonyBot/projects/retirement-planner/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/AnthonyBot/projects/retirement-planner/media/;
    }

    listen 80;
}
