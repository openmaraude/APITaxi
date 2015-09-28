set -x
set -e
if [ ! -e redis/src/redis-server ]; then
    wget https://github.com/mattsta/redis/archive/dynamic-redis-2.8.zip
    unzip dynamic-redis-2.8.zip
    rm dynamic-redis-2.8.zip
    mv redis-dynamic-redis-2.8 redis
    cd redis/
    make
    cd ..
fi
