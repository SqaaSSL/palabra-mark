#!/bin/sh
# Builds the two wideband mobile codecs that ffmpeg cannot encode, into research/codecs/bin:
#   amrwb-enc   AMR-WB encoder (VisualOn, Apache 2.0)
#   EVS_cod, EVS_dec   EVS encoder and decoder (3GPP TS 26.443 floating-point reference code)
# Needs a C compiler, make, curl and unzip. Works on macOS and Linux.
# The 3GPP code is downloaded from 3gpp.org and is not redistributed here: it is under 3GPP's own copyright terms.
set -e
here="$(cd "$(dirname "$0")" && pwd)"; dst="$here/codecs"; mkdir -p "$dst/bin" "$dst/src"; cd "$dst/src"

if [ ! -x "$dst/bin/amrwb-enc" ]; then
  curl -sL -o vo-amrwbenc.tar.gz https://downloads.sourceforge.net/project/opencore-amr/vo-amrwbenc/vo-amrwbenc-0.1.3.tar.gz
  tar xzf vo-amrwbenc.tar.gz
  (cd vo-amrwbenc-0.1.3 && ./configure --enable-example --disable-shared --quiet && make -s -j8 && cp amrwb-enc "$dst/bin/")
fi

if [ ! -x "$dst/bin/EVS_cod" ]; then
  curl -sL -o evs.zip https://www.3gpp.org/ftp/Specs/archive/26_series/26.443/26443-j00.zip
  rm -rf evs && mkdir evs && (cd evs && unzip -q ../evs.zip && for z in *.zip; do [ -f "$z" ] && unzip -q -o "$z"; done; true)
  mk="$(find evs -name Makefile | head -1)"
  (cd "$(dirname "$mk")" && make -s -j8 && cp EVS_cod EVS_dec "$dst/bin/")
fi
ls -l "$dst/bin"
