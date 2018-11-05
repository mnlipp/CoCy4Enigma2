#!/bin/bash
rm -rf build
mkdir -p build/usr/lib/enigma2/python/Plugins/SystemPlugins/
find CoCy -name \*.py | cpio -pvduma build/usr/lib/enigma2/python/Plugins/SystemPlugins/
mkdir -p build/tmp/cocy-install/
cp ez_setup.py build/tmp/cocy-install/
(cd build; tar cvzf data.tar.gz ./usr ./tmp)
(cd DEBIAN; tar cvzf ../build/control.tar.gz ./*)
(cd build; echo "2.0" > debian-binary)
VERSION=`fgrep Version: DEBIAN/control | sed -e 's/Version: *//'`
mkdir -p dist
rm -f dist/enigma2-plugin-extensions-cocy_${VERSION}.ipk
(cd build; ar -r ../dist/enigma2-plugin-extensions-cocy_${VERSION}.ipk ./debian-binary ./*.tar.gz)
(cd dist; ar t enigma2-plugin-extensions-cocy_${VERSION}.ipk)
