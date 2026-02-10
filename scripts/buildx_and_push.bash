export tag="1.7.0a1"
export game="swimming_squid_battle"
export pge_ver="PGE20251014"

docker buildx build --platform linux/amd64,linux/arm64 \
-t paiatech/${game}:${tag} -t paiatech/${game}:${tag}-${pge_ver} \
-f ./Dockerfile . --push