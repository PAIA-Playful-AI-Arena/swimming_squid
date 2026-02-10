export tag="2.5.1"
export game="swimming_squid"
export pge_ver="PGE20250522"

docker buildx build --platform linux/amd64,linux/arm64 \
-t paiatech/${game}:${tag} -t paiatech/${game}:${tag}-${pge_ver} \
-f ./Dockerfile . --push