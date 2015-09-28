set -x
set -e
if [ ! -e krmt/geo.so ]; then
    wget https://github.com/mattsta/krmt/archive/master.zip -O krmt.zip
    unzip krmt.zip
    rm krmt.zip
    mv krmt-master krmt
    cd krmt
    make
    cd ..
fi
