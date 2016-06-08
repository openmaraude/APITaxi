set -x
set -e
if [ ! -e redis/src/redis-server ]; then
    wget https://github.com/antirez/redis/archive/3.2.0.zip
    unzip 3.2.0.zip
    rm 3.2.0.zip
    mv redis-3.2.0 redis
    cd redis/
    make
    cd ..
fi
