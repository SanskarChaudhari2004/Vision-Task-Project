# Vision Task - Healthcare Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying Vision Task in a healthcare administrative environment, with emphasis on HIPAA compliance, data security, and healthcare workflow integration.

## Pre-Deployment Checklist

### Compliance & Legal
- [ ] Review HIPAA requirements for your healthcare organization
- [ ] Consult with your IT security team
- [ ] Document data protection policies
- [ ] Establish audit trail retention policies
- [ ] Create user access request and revocation procedures
- [ ] Develop incident response procedures

### infrastructure
- [ ] Identify hosting environment (on-premise vs cloud)
- [ ] Plan for backup and disaster recovery
- [ ] Prepare SSL/TLS certificates
- [ ] Design network architecture and firewalls
- [ ] Plan for high availability and redundancy
- [ ] Set up monitoring and alerting systems

### Security
- [ ] Implement password management (Argon2 hashing, minimum 12 characters)
- [ ] Plan multi-factor authentication (MFA)
- [ ] Configure network access controls
- [ ] Plan for role-based access control (RBAC) implementation
- [ ] Schedule security audit and penetration testing
- [ ] Plan for regular security updates

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+ LTS recommended), Windows Server 2019+, or macOS 12+
- **Python**: 3.8 or higher
- **RAM**: 4GB minimum
- **Storage**: 50GB minimum (adjust based on task volume)
- **Database**: PostgreSQL 12+ or MySQL 8.0+
- **Web Server**: Nginx or Apache
- **SSL**: Valid TLS certificate for HTTPS

### Recommended Production Setup
- **OS**: Ubuntu 20.04 LTS or CentOS 8+
- **Python**: 3.10+
- **RAM**: 16GB or more
- **Storage**: SSD with RAID-1 or better
- **Database**: PostgreSQL 14+ with replication
- **Web Server**: Nginx with load balancing
- **Reverse Proxy**: HAProxy or AWS ELB
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or CloudWatch

## Phase 1: Pre-Production Setup

### 1. Install Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3-pip
sudo apt-get install -y postgresql postgresql-contrib
sudo apt-get install -y nginx
sudo apt-get install -y git curl wget
```

**CentOS/RHEL:**
```bash
sudo dnf install python3.10 python3.10-devel postgresql postgresql-server
sudo dnf install nginx
sudo dnf install git curl wget
```

### 2. Create Application User

```bash
sudo useradd -m -s /bin/bash -d /opt/vision-task vision-user
sudo passwd vision-user
```

### 3. Set up Database

**PostgreSQL Setup:**

```bash
# As root or with sudo
sudo -u postgres psql

# Create database and user
CREATE DATABASE vision_task;
CREATE USER vision_app WITH PASSWORD 'secure_password_here';
ALTER ROLE vision_app SET client_encoding TO 'utf8';
ALTER ROLE vision_app SET default_transaction_isolation TO 'read committed';
ALTER ROLE vision_app SET default_transaction_deferrable TO on;
ALTER ROLE vision_app SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE vision_task TO vision_app;
ALTER DATABASE vision_task OWNER TO vision_app;
```

### 4. Configure Python Virtual Environment

```bash
sudo su - vision-user
cd ~/vision-task
python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install gunicorn psycopg2-binary python-dotenv
```

## Phase 2: Application Configuration

### 1. Create Environment Configuration

Create `.env` file (NEVER commit to version control):

```bash
# Security
SECRET_KEY=your-secret-key-min-32-chars-here
DEBUG=False
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://vision_app:secure_password@localhost:5432/vision_task

# Application
APP_HOST=0.0.0.0
APP_PORT=5000
WORKERS=4

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/vision-task/activity.log
LOG_MAX_BYTES=10485760  # 10MB
LOG_BACKUP_COUNT=10

# Email (for alerts and notifications)
SMTP_SERVER=your-mail-server.com
SMTP_PORT=587
SMTP_USERNAME=alerts@healthcare.org
SMTP_PASSWORD=smtp-password

# Healthcare Settings
ORGANIZATION_NAME="Your Healthcare Organization"
HEALTHCARE_DEPARTMENT="Administration"
```

### 2. Create Application Structure

```bash
sudo mkdir -p /opt/vision-task
sudo mkdir -p /var/log/vision-task
sudo mkdir -p /var/cache/vision-task
sudo chown vision-user:vision-user /opt/vision-task
sudo chown vision-user:vision-user /var/log/vision-task
sudo chown vision-user:vision-user /var/cache/vision-task
```

### 3. Database Migration

Create `database/schema.sql` for healthcare task management:

```sql
-- Core tables (example schema)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    department VARCHAR(100),
    roles TEXT[],
    can_view_high_sensitivity BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_login TIMESTAMP
);

CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sensitivity VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'new',
    priority INTEGER DEFAULT 0,
    created_by VARCHAR(255) NOT NULL REFERENCES users(username),
    assigned_to VARCHAR(255) REFERENCES users(username),
    department VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255),
    action VARCHAR(50),
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    status VARCHAR(20),
    details JSONB,
    ip_address INET
);

-- Indexes for performance
CREATE INDEX idx_tasks_created_by ON tasks(created_by);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);
CREATE INDEX idx_tasks_sensitivity ON tasks(sensitivity);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
```

Run migration:
```bash
psql -U vision_app -d vision_task < database/schema.sql
```

## Phase 3: Web Server Configuration

### Nginx Configuration

Create `/etc/nginx/sites-available/vision-task`:

```nginx
upstream vision_task {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name vision-task.healthcare.org;
    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    server_name vision-task.healthcare.org;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/vision-task.crt;
    ssl_certificate_key /etc/ssl/private/vision-task.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Logging
    access_log /var/log/nginx/vision-task-access.log;
    error_log /var/log/nginx/vision-task-error.log warn;

    # Limits
    client_max_body_size 10m;
    proxy_connect_timeout 60s;
    proxy_send_timeout 60s;
    proxy_read_timeout 60s;

    location / {
        proxy_pass http://vision_task;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/vision-task/vision_task/static;
        expires 30d;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/vision-task /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Systemd Service Configuration

Create `/etc/systemd/system/vision-task.service`:

```ini
[Unit]
Description=Vision Task - Healthcare Task Management System
After=network.target postgresql.service
Documentation=https://github.com/your-org/vision-task

[Service]
Type=notify
User=vision-user
WorkingDirectory=/opt/vision-task
Environment="PATH=/opt/vision-task/venv/bin"
EnvironmentFile=/opt/vision-task/.env

ExecStart=/opt/vision-task/venv/bin/gunicorn \
    --workers=4 \
    --worker-class=sync \
    --bind=127.0.0.1:5000 \
    --timeout=30 \
    --access-logfile=/var/log/vision-task/gunicorn-access.log \
    --error-logfile=/var/log/vision-task/gunicorn-error.log \
    --log-level=info \
    vision_task:create_app

# Auto-restart on failure
Restart=always
RestartSec=10

# Security Settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable vision-task
sudo systemctl start vision-task
sudo systemctl status vision-task
```

## Phase 4: Security Hardening

### 1. Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5432/tcp from internal-network
sudo ufw enable

# firewalld (CentOS)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### 2. Enable Audit Logging

```bash
# auditd for system-level logging
sudo apt-get install auditd
sudo systemctl enable auditd
sudo systemctl start auditd

# Add custom audit rules
sudo auditctl -w /opt/vision-task -p wa -k vision_task
sudo auditctl -w /var/log/vision-task -p wa -k vision_task_logs
```

### 3. File Permissions

```bash
sudo chown -R vision-user:vision-user /opt/vision-task
sudo chmod 750 /opt/vision-task
sudo chmod 640 /opt/vision-task/.env  # Keep .env secure
sudo chmod 755 /var/log/vision-task
```

### 4. Backup Encryption

```bash
# Create encrypted backup script
sudo cat > /usr/local/bin/backup-vision-task.sh <<'EOF'
#!/bin/bash
BACKUP_DIR="/backups/vision-task"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
pg_dump -U vision_app -h localhost vision_task | \
  openssl enc -aes-256-cbc -salt -out "${BACKUP_DIR}/db_${DATE}.sql.enc"

# Application backup (excluding venv)
tar czf - /opt/vision-task \
  --exclude='venv' --exclude='__pycache__' \
  --exclude='.git' --exclude='*.pyc' | \
  openssl enc -aes-256-cbc -salt -out "${BACKUP_DIR}/app_${DATE}.tar.gz.enc"

# Cleanup old backups (keep 30 days)
find ${BACKUP_DIR} -type f -mtime +30 -delete
EOF

sudo chmod +x /usr/local/bin/backup-vision-task.sh

# Add to crontab
sudo crontab -e  # Add: 0 2 * * * /usr/local/bin/backup-vision-task.sh
```

## Phase 5: Monitoring & Alerting

### 1. System Monitoring

Install Prometheus + Node Exporter:

```bash
# Node Exporter for system metrics
wget https://github.com/prometheus/node_exporter/releases/download/v1.3.1/node_exporter-1.3.1.linux-amd64.tar.gz
tar xzf node_exporter-1.3.1.linux-amd64.tar.gz
sudo cp node_exporter-1.3.1.linux-amd64/node_exporter /usr/local/bin/
```

### 2. Application Monitoring

Add health check endpoint to application:

```python
@app.route('/health', methods=['GET'])
def health_check():
    # Check database connection
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except:
        db_status = 'unhealthy'
    
    return jsonify({
        'status': db_status,
        'timestamp': datetime.utcnow().isoformat()
    }), 200 if db_status == 'healthy' else 503
```

### 3. Logging Aggregation

Setup ELK Stack or CloudWatch:

```yaml
# logstash configuration
input {
  file {
    path => "/var/log/vision-task/activity.log"
    start_position => "beginning"
  }
}

filter {
  json {
    source => "message"
  }
}

output {
  elasticsearch {
    hosts => "elasticsearch:9200"
    index => "vision-task-%{+YYYY.MM.dd}"
  }
}
```

## Phase 6: Healthcare Integration

### HIPAA Compliance Checklist

- [ ] Implement proper authentication (not bearer tokens)
- [ ] Enable encryption at rest (database encryption)
- [ ] Enable encryption in transit (HTTPS/TLS)
- [ ] Implement audit logging with tamper detection
- [ ] Set up backup and disaster recovery
- [ ] Implement access controls and RBAC
- [ ] Establish user access review procedures
- [ ] Configure automatic lockdown on suspicious activity
- [ ] Schedule regular security assessments
- [ ] Document all security controls in compliance manual
- [ ] Conduct staff training on data protection

### EHR Integration

```python
# Example: HL7 FHIR integration
import requests

def sync_patient_data(patient_id):
    fhir_url = "https://ehr-system.healthcare.org/fhir"
    headers = {
        "Authorization": f"Bearer {ehr_token}",
        "Content-Type": "application/fhir+json"
    }
    
    # Fetch patient data from EHR
    response = requests.get(
        f"{fhir_url}/Patient/{patient_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        patient_data = response.json()
        # Sync to Vision Task
        create_task_from_ehr(patient_data)
```

## Phase 7: Post-Deployment

### 1. Initial Testing

- [ ] Test user login and session management
- [ ] Verify task creation and filtering
- [ ] Test role-based access control
- [ ] Verify audit logging
- [ ] Test backup and restore procedures
- [ ] Verify SSL/TLS configuration
- [ ] Test email notifications (if configured)
- [ ] Performance load testing

### 2. User Training

- [ ] Create user documentation
- [ ] Conduct staff training sessions
- [ ] Establish support procedures
- [ ] Create incident response playbooks

### 3. Ongoing Operations

- [ ] Monitor system performance daily
- [ ] Review audit logs regularly
- [ ] Update dependencies monthly
- [ ] Schedule security assessments quarterly
- [ ] Conduct backup recovery drills quarterly
- [ ] Review and update access controls quarterly
- [ ] Update security documentation annually

## Troubleshooting

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql -U vision_app -h localhost -d vision_task -c "SELECT 1"

# Check connection logs
sudo journalctl -u postgresql -f
```

### Application Not Starting
```bash
# Check systemd status
sudo systemctl status vision-task
sudo journalctl -u vision-task -f

# Check error logs
tail -f /var/log/vision-task/gunicorn-error.log
```

### SSL Certificate Issues
```bash
# Verify certificate
openssl x509 -in /etc/ssl/certs/vision-task.crt -text -noout

# Test HTTPS
curl -v https://vision-task.healthcare.org/health
```

## Security Audit Checklist

Regular audits (every 3-6 months):

- [ ] Review and update access control list
- [ ] Audit user accounts for inactive users
- [ ] Review recent security bulletins
- [ ] Test backup restoration
- [ ] Check SSL certificate expiration dates
- [ ] Review firewall rules
- [ ] Analyze audit logs for suspicious activity
- [ ] Conduct vulnerability scan (Nessus, OpenVAS)
- [ ] Review password policies compliance
- [ ] Test disaster recovery procedures

## Support & Escalation

For production issues:

1. Check system status: `systemctl status vision-task`
2. Review logs: `/var/log/vision-task/`
3. Check database: `psql vision_task -c "SELECT count(*) FROM tasks"`
4. Contact: ops-team@healthcare.org

---

## References

- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [OWASP Application Security](https://owasp.org/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)

---

For additional support or questions, contact the Vision Task development team.
