set -x
set -e
if [ ! -e yajl/build/yajl-*/bin/json_reformat ]; then
    wget https://github.com/lloyd/yajl/archive/master.zip -O yajl.zip
    unzip yajl.zip
    rm yajl.zip
    mv yajl-master yajl
    cd yajl
    ./configure
    make
    cd ..
fi
