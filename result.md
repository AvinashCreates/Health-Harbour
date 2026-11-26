[pamarthi-avinash@archlinux healthcare-exchange]$ curl -i --max-time 10 http://127.0.0.1:8000/health
curl: (28) Operation timed out after 10001 milliseconds with 0 bytes received
[pamarthi-avinash@archlinux healthcare-exchange]$ printf '%s\n' '--- Compose port mappings ---'
docker compose port backend 8000
docker compose port hapi 8080
printf '%s\n' '--- Container IPs ---'
docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}} {{json .NetworkSettings.Ports}}' healthcare-exchange-backend-1 healthcare-exchange-hapi-1
printf '%s\n' '--- Host listeners ---'
sudo ss -ltnp | grep -E ':8000|:8081' || true
printf '%s\n' '--- API login status (token hidden) ---'
docker compose exec -T backend python - <<'PY'
import json, urllib.error, urllib.request
req=urllib.request.Request('http://127.0.0.1:8000/auth/login', data=json.dumps({'email':'admin@example.com','password':'<redacted>'}).encode(), headers={'Content-Type':'application/json'}, method='POST')
try:
with urllib.request.urlopen(req, timeout=10) as r:
d=json.load(r); print('HTTP',r.status,'role',d.get('user',{}).get('role'),'token_returned',bool(d.get('access_token')))
except urllib.error.HTTPError as e:
print('HTTP',e.code,e.read().decode()[:300])
except Exception as e:
print(type(e).__name__,str(e))
PY
--- Compose port mappings ---
127.0.0.1:8000
127.0.0.1:8081
--- Container IPs ---
/healthcare-exchange-backend-1 172.19.0.2 {"8000/tcp":[{"HostIp":"127.0.0.1","HostPort":"8000"}]}
/healthcare-exchange-hapi-1 172.19.0.4 {"8080/tcp":[{"HostIp":"127.0.0.1","HostPort":"8081"}]}
--- Host listeners ---
[sudo] password for pamarthi-avinash: 
LISTEN 0      4096       127.0.0.1:8000       0.0.0.0:*    users:(("docker-proxy",pid=106749,fd=7))
LISTEN 0      4096       127.0.0.1:8081       0.0.0.0:*    users:(("docker-proxy",pid=128772,fd=7))
--- API login status (token hidden) ---
  File "<stdin>", line 4
    with urllib.request.urlopen(req, timeout=10) as r:
    ^^^^
IndentationError: expected an indented block after 'try' statement on line 3
[pamarthi-avinash@archlinux healthcare-exchange]$ printf '%s\n' '--- Host to backend container IP ---'
curl --noproxy '*' -i --connect-timeout 2 --max-time 5 http://172.19.0.2:8000/
printf '%s\n' '--- Host to HAPI container IP ---'
curl --noproxy '*' -i --connect-timeout 2 --max-time 5 http://172.19.0.4:8080/fhir/metadata
printf '%s\n' '--- Login inside backend (prints no token) ---'
docker compose exec -T backend python -c 'import json,urllib.request; q=urllib.request.Request("http://127.0.0.1:8000/auth/login",data=json.dumps({"email":"admin@example.com","password":"<redacted>"}).encode(),headers={"Content-Type":"application/json"},method="POST"); r=urllib.request.urlopen(q,timeout=10); d=json.load(r); print("HTTP",r.status,"role",d.get("user",{}).get("role"),"token_returned",bool(d.get("access_token")))'
--- Host to backend container IP ---
curl: (28) Connection timed out after 2001 milliseconds
--- Host to HAPI container IP ---
curl: (28) Connection timed out after 2001 milliseconds
--- Login inside backend (prints no token) ---
HTTP 200 role admin token_returned True
[pamarthi-avinash@archlinux healthcare-exchange]$ printf '%s\n' '--- Docker networking mode ---'
docker info | grep -iE 'rootless|iptables|firewall|network'
printf '%s\n' '--- Compose bridge ---'
docker network inspect healthcare-exchange_default --format '{{json .IPAM.Config}} {{json .Options}} {{json .Containers}}'
printf '%s\n' '--- Host route to backend container ---'
ip route get 172.19.0.2
printf '%s\n' '--- Firewall services ---'
for svc in docker firewalld nftables; do printf "$svc: "; systemctl is-active "$svc" 2>/dev/null || true; done
printf '%s\n' '--- Docker-related firewall rules ---'
sudo nft list ruleset 2>/dev/null | grep -iE 'docker|172\.19|8000|8081|drop|reject' | head -80
--- Docker networking mode ---
  Network: bridge host ipvlan macvlan null overlay
 Firewall Backend: iptables
--- Compose bridge ---
[{"Subnet":"172.19.0.0/16","Gateway":"172.19.0.1"}] {} {"03251fb01c97a0e426459d30dfaf30fb888921a0a8d8c2b836ab9a6783b2c0ec":{"Name":"healthcare-exchange-hapi-1","EndpointID":"55a7eb5f374e6a7c903ebffa115ef898e43ac532c97240a4f048fdb6db98b805","MacAddress":"0e:8a:77:9a:d0:20","IPv4Address":"172.19.0.4/16","IPv6Address":""},"9f6cf1fe34a3d63bca1fc90536716db01aae860fe541efa91d0e86c7c17d6f6c":{"Name":"healthcare-exchange-backend-1","EndpointID":"c93b2c7ed7b8f0e5bdfe18daaeecc3dee0e12aea9d2446ce4d6ba91c6f7a0460","MacAddress":"12:3b:c4:ea:b9:c9","IPv4Address":"172.19.0.2/16","IPv6Address":""},"ed0f2b0dda26434f47ed0afe8473fa4b77ccb430379fb211c7991dbb08d405d2":{"Name":"healthcare-exchange-db-1","EndpointID":"ec04fb679f7dcef7a51c16f24f1c607062f06aaefd4e91b267aa491f79a80ceb","MacAddress":"c6:e6:9f:69:5e:e8","IPv4Address":"172.19.0.3/16","IPv6Address":""}}
--- Host route to backend container ---
172.19.0.2 via 10.76.199.230 dev wlp4s0 src 10.76.199.67 uid 1000 
    cache 
--- Firewall services ---
docker: active
firewalld: inactive
nftables: inactive
--- Docker-related firewall rules ---
                xt match "conntrack" counter packets 0 bytes 0 drop
        chain ufw-reject-input {
        chain ufw-reject-output {
        chain ufw-reject-forward {
                counter packets 80 bytes 6320 jump ufw-reject-input
                counter packets 14661 bytes 3325006 jump ufw-reject-output
                type filter hook forward priority filter; policy drop;
                counter packets 0 bytes 0 jump DOCKER-USER
                counter packets 0 bytes 0 jump DOCKER-FORWARD
                counter packets 0 bytes 0 jump ufw-reject-forward
                counter packets 0 bytes 0 drop
                counter packets 0 bytes 0 drop
                counter packets 0 bytes 0 xt target "REJECT"
        chain DOCKER {
                ip daddr 172.19.0.4 iifname != "br-7dc8efe54912" oifname "br-7dc8efe54912" tcp dport 8080 counter packets 0 bytes 0 accept
                ip daddr 172.19.0.2 iifname != "br-7dc8efe54912" oifname "br-7dc8efe54912" tcp dport 8000 counter packets 0 bytes 0 accept
                ip daddr 172.19.0.3 iifname != "br-7dc8efe54912" oifname "br-7dc8efe54912" tcp dport 5432 counter packets 0 bytes 0 accept
                ip daddr 172.17.0.2 iifname != "docker0" oifname "docker0" tcp dport 8080 counter packets 0 bytes 0 accept
                iifname != "br-6557a9d90e2a" oifname "br-6557a9d90e2a" counter packets 0 bytes 0 drop
                iifname != "br-7dc8efe54912" oifname "br-7dc8efe54912" counter packets 0 bytes 0 drop
                iifname != "docker0" oifname "docker0" counter packets 0 bytes 0 drop
        chain DOCKER-FORWARD {
                counter packets 0 bytes 0 jump DOCKER-CT
                counter packets 0 bytes 0 jump DOCKER-INTERNAL
                counter packets 0 bytes 0 jump DOCKER-BRIDGE
                iifname "docker0" counter packets 0 bytes 0 accept
        chain DOCKER-BRIDGE {
                oifname "br-6557a9d90e2a" counter packets 0 bytes 0 jump DOCKER
                oifname "br-7dc8efe54912" counter packets 0 bytes 0 jump DOCKER
                oifname "docker0" counter packets 0 bytes 0 jump DOCKER
        chain DOCKER-CT {
                oifname "docker0" xt match "conntrack" counter packets 0 bytes 0 accept
        chain DOCKER-INTERNAL {
        chain DOCKER-USER {
                xt match "rt" counter packets 0 bytes 0 drop
                xt match "conntrack" counter packets 4 bytes 240 drop
                xt match "rt" counter packets 0 bytes 0 drop
                xt match "rt" counter packets 0 bytes 0 drop
        chain ufw6-reject-input {
        chain ufw6-reject-output {
        chain ufw6-reject-forward {
                counter packets 0 bytes 0 jump ufw6-reject-input
                counter packets 10447 bytes 6617201 jump ufw6-reject-output
                type filter hook forward priority filter; policy drop;
                counter packets 0 bytes 0 jump DOCKER-USER
                counter packets 0 bytes 0 jump DOCKER-FORWARD
                counter packets 0 bytes 0 jump ufw6-reject-forward
                counter packets 0 bytes 0 drop
                counter packets 0 bytes 0 xt target "REJECT"
        chain DOCKER {
        chain DOCKER-FORWARD {
                counter packets 0 bytes 0 jump DOCKER-CT
                counter packets 0 bytes 0 jump DOCKER-INTERNAL
                counter packets 0 bytes 0 jump DOCKER-BRIDGE
        chain DOCKER-BRIDGE {
        chain DOCKER-CT {
        chain DOCKER-INTERNAL {
        chain DOCKER-USER {
        chain DOCKER {
                iifname != "docker0" tcp dport 8080 counter packets 0 bytes 0 xt target "DNAT"
                ip daddr 127.0.0.1 iifname != "br-7dc8efe54912" tcp dport 8000 counter packets 0 bytes 0 xt target "DNAT"
                ip daddr 127.0.0.1 iifname != "br-7dc8efe54912" tcp dport 8081 counter packets 0 bytes 0 xt target "DNAT"
                xt match "addrtype" counter packets 0 bytes 0 jump DOCKER
                ip daddr != 127.0.0.0/8 xt match "addrtype" counter packets 0 bytes 0 jump DOCKER
                ip saddr 172.17.0.0/16 oifname != "docker0" counter packets 0 bytes 0 xt target "MASQUERADE"
                ip saddr 172.19.0.0/16 oifname != "br-7dc8efe54912" counter packets 0 bytes 0 xt target "MASQUERADE"
        chain DOCKER {
                xt match "addrtype" counter packets 4 bytes 224 jump DOCKER
                ip6 daddr != ::1 xt match "addrtype" counter packets 1778 bytes 526288 jump DOCKER
                ip daddr 172.18.0.2 iifname != "br-6557a9d90e2a" counter packets 0 bytes 0 drop
                ip daddr 172.17.0.2 iifname != "docker0" counter packets 0 bytes 0 drop
                ip daddr 172.19.0.3 iifname != "br-7dc8efe54912" counter packets 0 bytes 0 drop
                ip daddr 127.0.0.1 iifname != "lo" tcp dport 5432 counter packets 0 bytes 0 drop
                ip daddr 172.19.0.2 iifname != "br-7dc8efe54912" counter packets 0 bytes 0 drop
                ip daddr 127.0.0.1 iifname != "lo" tcp dport 8000 counter packets 0 bytes 0 drop
                ip daddr 172.19.0.4 iifname != "br-7dc8efe54912" counter packets 0 bytes 0 drop
                ip daddr 127.0.0.1 iifname != "lo" tcp dport 8081 counter packets 0 bytes 0 drop
[pamarthi-avinash@archlinux healthcare-exchange]$ printf '%s\n' '--- bridge interface ---'
ip -br addr show br-7dc8efe54912
printf '%s\n' '--- routes matching Docker subnet ---'
ip route show table all | grep -E '172\.19|172\.16|172\.17|172\.18|172\.20|10\.76' || true
printf '%s\n' '--- route decisions ---'
ip route get 172.19.0.1
ip route get 172.19.0.2
printf '%s\n' '--- other Docker network subnets ---'
docker network ls -q | xargs -r docker network inspect --format '{{.Name}} {{range .IPAM.Config}}{{.Subnet}} {{end}}'
--- bridge interface ---
br-7dc8efe54912  UP             
--- routes matching Docker subnet ---
default via 10.76.199.230 dev wlp4s0 proto dhcp src 10.76.199.67 metric 600 
10.76.199.0/24 dev wlp4s0 proto kernel scope link src 10.76.199.67 metric 600 
local 10.76.199.67 dev wlp4s0 table local proto kernel scope host src 10.76.199.67 
broadcast 10.76.199.255 dev wlp4s0 table local proto kernel scope link src 10.76.199.67 
--- route decisions ---
172.19.0.1 via 10.76.199.230 dev wlp4s0 src 10.76.199.67 uid 1000 
    cache 
172.19.0.2 via 10.76.199.230 dev wlp4s0 src 10.76.199.67 uid 1000 
    cache 
--- other Docker network subnets ---
bridge 172.17.0.0/16 
healthcare-exchange_default 172.19.0.0/16 
host 
none 
wirachain-docker-main_default 172.18.0.0/16 
[pamarthi-avinash@archlinux healthcare-exchange]$ docker compose down
docker compose --profile fhir up -d db backend hapi
[+] down 3/3
 ✔ Container healthcare-exchange-backend-1 Removed                                                                              11.0s
 ✔ Container healthcare-exchange-db-1      Removed                                                                               0.3s
 ! Network healthcare-exchange_default     Resource is still in use                                                              0.0s
[+] up 3/3
 ✔ Container healthcare-exchange-hapi-1    Running                                                                               0.0s
 ✔ Container healthcare-exchange-db-1      Healthy                                                                               6.1s
 ✔ Container healthcare-exchange-backend-1 Started                                                                               6.9s
[pamarthi-avinash@archlinux healthcare-exchange]$ ip -br addr | grep br-
ip route get 172.19.0.2
br-6557a9d90e2a  UP             
br-7dc8efe54912  UP             
172.19.0.2 via 10.76.199.230 dev wlp4s0 src 10.76.199.67 uid 1000 
    cache 
[pamarthi-avinash@archlinux healthcare-exchange]$ curl -i --max-time 10 http://127.0.0.1:8081/fhir/metadata
curl -i --max-time 10 http://127.0.0.1:8000/health
curl: (28) Operation timed out after 10002 milliseconds with 0 bytes received
curl: (28) Operation timed out after 10001 milliseconds with 0 bytes received
[pamarthi-avinash@archlinux healthcare-exchange]$ 
